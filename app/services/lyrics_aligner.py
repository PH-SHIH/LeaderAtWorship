"""Anchor-based lyrics alignment engine (v2).

Core algorithm:
1. Extract high-confidence anchor points between Whisper segments and GT lyrics
2. Warp GT timeline using anchor pairs as control points
3. Interpolate timestamps for non-anchor GT lines
4. Detect phantom lines (GT lines with no Whisper evidence)
5. Optional BPM beat-snap

Output is GT-driven: one segment per GT lyric line (complete lyrics).
Falls back to greedy matching when anchor coverage is insufficient.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass

from app.utils.lrc_parser import LrcLine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AnchorPoint:
    """A high-confidence pairing between a Whisper segment and a GT line."""

    gt_index: int
    whisper_index: int
    gt_time_ms: int
    whisper_start_ms: int
    whisper_end_ms: int
    fuzzy_score: float
    combined_score: float


@dataclass
class AlignedSegment:
    """A single aligned subtitle segment."""

    start_ms: int
    end_ms: int
    text: str  # GT text (Traditional Chinese) or original Whisper
    text_secondary: str | None  # Original Whisper text (anchors only)
    confidence: float  # [0.0, 1.0]
    gt_index: int | None
    source_type: str  # "anchor" | "interpolated" | "extrapolated" | "phantom" | "greedy"


@dataclass
class AlignmentResult:
    """Complete result of the alignment process."""

    segments: list[AlignedSegment]
    matched_count: int
    unmatched_count: int
    average_confidence: float
    gt_lines_used: int
    gt_lines_total: int
    algorithm: str  # "anchor" | "greedy_fallback"


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def _normalize_chinese(text: str) -> str:
    """Normalize text for fuzzy comparison.

    1. Traditional Chinese -> Simplified Chinese (OpenCC s2t)
    2. NFKC unicode normalization (fullwidth -> halfwidth)
    3. Remove all punctuation (Chinese + Western)
    4. Remove all whitespace (Chinese doesn't need spaces)
    5. Lowercase
    """
    text = _get_opencc("t2s").convert(text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\w]", "", text, flags=re.UNICODE)
    text = text.replace("_", "")
    return text.lower()


# Module-level cache for OpenCC converters (they're expensive to create)
_opencc_cache: dict[str, object] = {}


def _get_opencc(config: str):
    """Get or create a cached OpenCC converter."""
    if config not in _opencc_cache:
        import opencc
        _opencc_cache[config] = opencc.OpenCC(config)
    return _opencc_cache[config]


def _to_traditional(text: str) -> str:
    """Convert text to Traditional Chinese for display output.

    Uses OpenCC s2twp (Simplified → Traditional, Taiwan phrases) for
    correct handling of ambiguous characters like 只/隻, 家/傢.
    """
    return _get_opencc("s2twp").convert(text)


# ---------------------------------------------------------------------------
# Phase 2: Anchor extraction (DP maximum-weight monotonic subsequence)
# ---------------------------------------------------------------------------

def _extract_anchors(
    whisper_segments: list[dict],
    gt_lines: list[LrcLine],
    w_norms: list[str],
    g_norms: list[str],
    anchor_threshold: float = 0.65,
    logprob_threshold: float = -0.7,
) -> list[AnchorPoint]:
    """Find high-confidence anchor pairings via DP.

    Builds candidate pairs above threshold, then finds the maximum-weight
    subset where both gt_index and whisper_index are strictly increasing.
    """
    from rapidfuzz import fuzz

    # Build candidate pairs
    candidates: list[AnchorPoint] = []

    for wi, w_seg in enumerate(whisper_segments):
        if not w_norms[wi]:
            continue
        w_mid = (w_seg["start_ms"] + w_seg["end_ms"]) // 2

        # Optional logprob filter
        logprob = w_seg.get("avg_logprob")
        if logprob is not None and logprob < logprob_threshold:
            continue

        for gi, gt_line in enumerate(gt_lines):
            if not g_norms[gi]:
                continue

            text_score = fuzz.ratio(w_norms[wi], g_norms[gi]) / 100.0
            time_score = 0.0
            if gt_line.time_ms > 0:
                time_diff = abs(w_mid - gt_line.time_ms)
                time_score = max(0.0, 1.0 - time_diff / 30_000)

            combined = text_score * 0.85 + time_score * 0.15

            if combined >= anchor_threshold:
                candidates.append(AnchorPoint(
                    gt_index=gi,
                    whisper_index=wi,
                    gt_time_ms=gt_line.time_ms,
                    whisper_start_ms=w_seg["start_ms"],
                    whisper_end_ms=w_seg["end_ms"],
                    fuzzy_score=text_score,
                    combined_score=combined,
                ))

    if not candidates:
        return []

    # Sort by (gt_index, whisper_index) for DP
    candidates.sort(key=lambda c: (c.gt_index, c.whisper_index))

    # DP: find maximum-weight strictly-increasing subsequence
    n = len(candidates)
    dp = [c.combined_score for c in candidates]
    parent = [-1] * n

    for i in range(1, n):
        for j in range(i):
            if (candidates[j].gt_index < candidates[i].gt_index
                    and candidates[j].whisper_index < candidates[i].whisper_index
                    and dp[j] + candidates[i].combined_score > dp[i]):
                dp[i] = dp[j] + candidates[i].combined_score
                parent[i] = j

    # Backtrack to find the best chain
    best_end = max(range(n), key=lambda i: dp[i])
    chain: list[AnchorPoint] = []
    idx = best_end
    while idx != -1:
        chain.append(candidates[idx])
        idx = parent[idx]
    chain.reverse()

    return chain


# ---------------------------------------------------------------------------
# Phase 3: Timeline warping + interpolation
# ---------------------------------------------------------------------------

def _warp_gt_lines(
    gt_lines: list[LrcLine],
    anchors: list[AnchorPoint],
    whisper_segments: list[dict],
    output_traditional: bool = True,
) -> list[AlignedSegment]:
    """Place every GT line using anchor-based timeline warping.

    For GT lines between two anchors: linear interpolation.
    For GT lines before first / after last anchor: extrapolation.
    Anchor GT lines get the Whisper timestamp directly.
    """
    # Build anchor lookup: gt_index -> AnchorPoint
    anchor_map: dict[int, AnchorPoint] = {a.gt_index: a for a in anchors}

    # Build whisper text lookup: whisper_index -> text
    whisper_text_map: dict[int, str] = {
        a.whisper_index: whisper_segments[a.whisper_index]["text"]
        for a in anchors
    }

    # Compute rate for extrapolation
    if len(anchors) >= 2:
        first, second = anchors[0], anchors[1]
        gt_span_start = second.gt_time_ms - first.gt_time_ms
        w_span_start = second.whisper_start_ms - first.whisper_start_ms
        rate_start = w_span_start / max(1, gt_span_start)

        last_prev, last = anchors[-2], anchors[-1]
        gt_span_end = last.gt_time_ms - last_prev.gt_time_ms
        w_span_end = last.whisper_start_ms - last_prev.whisper_start_ms
        rate_end = w_span_end / max(1, gt_span_end)
    else:
        rate_start = 1.0
        rate_end = 1.0

    last_whisper_end = max(s["end_ms"] for s in whisper_segments)
    segments: list[AlignedSegment] = []

    for gi, gt_line in enumerate(gt_lines):
        text = _to_traditional(gt_line.text) if output_traditional else gt_line.text

        if gi in anchor_map:
            # Anchor: use Whisper timestamp directly
            anchor = anchor_map[gi]
            segments.append(AlignedSegment(
                start_ms=anchor.whisper_start_ms,
                end_ms=anchor.whisper_end_ms,
                text=text,
                text_secondary=whisper_text_map.get(anchor.whisper_index),
                confidence=anchor.fuzzy_score,
                gt_index=gi,
                source_type="anchor",
            ))
            continue

        gt_time = gt_line.time_ms

        # Find surrounding anchors
        anchor_before = None
        anchor_after = None
        for a in anchors:
            if a.gt_index < gi:
                anchor_before = a
            elif a.gt_index > gi and anchor_after is None:
                anchor_after = a
                break

        if anchor_before is not None and anchor_after is not None:
            # Interpolation: between two anchors
            gt_span = anchor_after.gt_time_ms - anchor_before.gt_time_ms
            if gt_span > 0:
                ratio = (gt_time - anchor_before.gt_time_ms) / gt_span
                whisper_span = anchor_after.whisper_start_ms - anchor_before.whisper_start_ms
                new_start = int(anchor_before.whisper_start_ms + ratio * whisper_span)
            else:
                new_start = anchor_before.whisper_start_ms

            # Confidence decays with distance from nearest anchor
            dist = min(gi - anchor_before.gt_index, anchor_after.gt_index - gi)
            confidence = max(0.3, 0.55 - 0.05 * dist)

            segments.append(AlignedSegment(
                start_ms=max(0, new_start),
                end_ms=0,  # Will be computed below
                text=text,
                text_secondary=None,
                confidence=confidence,
                gt_index=gi,
                source_type="interpolated",
            ))

        elif anchor_before is not None:
            # Extrapolation: after last anchor
            offset = gt_time - anchor_before.gt_time_ms
            new_start = int(anchor_before.whisper_start_ms + offset * rate_end)
            new_start = max(0, min(new_start, last_whisper_end))

            segments.append(AlignedSegment(
                start_ms=new_start,
                end_ms=0,
                text=text,
                text_secondary=None,
                confidence=0.25,
                gt_index=gi,
                source_type="extrapolated",
            ))

        elif anchor_after is not None:
            # Extrapolation: before first anchor
            offset = gt_time - anchor_after.gt_time_ms  # negative
            new_start = int(anchor_after.whisper_start_ms + offset * rate_start)
            new_start = max(0, new_start)

            segments.append(AlignedSegment(
                start_ms=new_start,
                end_ms=0,
                text=text,
                text_secondary=None,
                confidence=0.25,
                gt_index=gi,
                source_type="extrapolated",
            ))

    # Compute end times: next line's start_ms - 50ms
    for i in range(len(segments)):
        if i < len(segments) - 1:
            segments[i].end_ms = max(segments[i].start_ms, segments[i + 1].start_ms - 50)
        else:
            segments[i].end_ms = max(segments[i].start_ms, last_whisper_end)

    return segments


# ---------------------------------------------------------------------------
# Phase 4: Phantom line detection
# ---------------------------------------------------------------------------

def _detect_phantoms(
    segments: list[AlignedSegment],
    whisper_segments: list[dict],
    phantom_threshold_ms: int = 3000,
) -> None:
    """Mark non-anchor segments as phantom if no Whisper segment is nearby.

    Also detects extrapolated lines that collapsed to the same timestamp
    (clamped to audio boundary) — these are beyond the audio range.
    """
    whisper_mids = [(s["start_ms"] + s["end_ms"]) // 2 for s in whisper_segments]
    last_whisper_end = max(s["end_ms"] for s in whisper_segments)

    for seg in segments:
        if seg.source_type == "anchor":
            continue

        # Extrapolated lines clamped to audio boundary are phantoms
        if seg.source_type == "extrapolated" and seg.start_ms >= last_whisper_end:
            seg.confidence = 0.1
            seg.source_type = "phantom"
            continue

        nearby = any(
            abs(wm - seg.start_ms) < phantom_threshold_ms
            for wm in whisper_mids
        )
        if not nearby:
            seg.confidence = 0.1
            seg.source_type = "phantom"


# ---------------------------------------------------------------------------
# Legacy greedy alignment (fallback)
# ---------------------------------------------------------------------------

def _greedy_align(
    whisper_segments: list[dict],
    gt_lines: list[LrcLine],
    w_norms: list[str],
    g_norms: list[str],
    match_threshold: float = 0.55,
    time_weight: float = 0.1,
    max_lookahead: int = 8,
    output_traditional: bool = True,
) -> AlignmentResult:
    """Original forward-only greedy matching (v1 algorithm).

    Used as fallback when anchor coverage is insufficient.
    """
    from rapidfuzz import fuzz

    aligned: list[AlignedSegment] = []
    gt_cursor = 0
    matched_count = 0
    confidences: list[float] = []

    for seg in whisper_segments:
        seg_text = seg["text"].strip()
        if not seg_text:
            aligned.append(AlignedSegment(
                start_ms=seg["start_ms"],
                end_ms=seg["end_ms"],
                text="",
                text_secondary=None,
                confidence=0.0,
                gt_index=None,
                source_type="greedy",
            ))
            continue

        whisper_norm = _normalize_chinese(seg_text)
        whisper_mid_ms = (seg["start_ms"] + seg["end_ms"]) // 2

        best_score = 0.0
        best_idx = -1

        search_end = min(gt_cursor + max_lookahead, len(gt_lines))

        for gi in range(gt_cursor, search_end):
            text_score = fuzz.ratio(whisper_norm, g_norms[gi]) / 100.0
            time_bonus = 0.0
            if gt_lines[gi].time_ms > 0:
                time_diff_ms = abs(whisper_mid_ms - gt_lines[gi].time_ms)
                time_bonus = max(0.0, 1.0 - (time_diff_ms / 15_000))
            combined = text_score * (1 - time_weight) + time_bonus * time_weight

            if combined > best_score:
                best_score = combined
                best_idx = gi

        if best_score >= match_threshold and best_idx >= 0:
            gt_text = gt_lines[best_idx].text
            if output_traditional:
                gt_text = _to_traditional(gt_text)
            aligned.append(AlignedSegment(
                start_ms=seg["start_ms"],
                end_ms=seg["end_ms"],
                text=gt_text,
                text_secondary=seg_text,
                confidence=best_score,
                gt_index=best_idx,
                source_type="greedy",
            ))
            gt_cursor = best_idx + 1
            matched_count += 1
            confidences.append(best_score)
        else:
            aligned.append(AlignedSegment(
                start_ms=seg["start_ms"],
                end_ms=seg["end_ms"],
                text=seg_text,
                text_secondary=None,
                confidence=0.0,
                gt_index=None,
                source_type="greedy",
            ))

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return AlignmentResult(
        segments=aligned,
        matched_count=matched_count,
        unmatched_count=len(whisper_segments) - matched_count,
        average_confidence=avg_confidence,
        gt_lines_used=gt_cursor,
        gt_lines_total=len(gt_lines),
        algorithm="greedy_fallback",
    )


# ---------------------------------------------------------------------------
# Main alignment entry point
# ---------------------------------------------------------------------------

def align(
    whisper_segments: list[dict],
    gt_lines: list[LrcLine],
    *,
    anchor_threshold: float = 0.65,
    logprob_threshold: float = -0.7,
    min_anchor_ratio: float = 0.4,
    match_threshold: float = 0.55,
    time_weight: float = 0.1,
    max_lookahead: int = 8,
    phantom_threshold_ms: int = 3000,
    output_traditional: bool = True,
) -> AlignmentResult:
    """Align Whisper segments with ground truth lyrics using anchor-based algorithm.

    Phase 1: Normalize all text
    Phase 2: Extract anchor points via DP (maximum-weight monotonic subsequence)
    Phase 3: Warp GT timeline using anchors, interpolate non-anchor lines
    Phase 4: Detect phantom lines (no Whisper evidence)

    Falls back to greedy matching if anchor coverage < min_anchor_ratio.

    Args:
        whisper_segments: Dicts with keys: start_ms, end_ms, text, avg_logprob (optional)
        gt_lines: Parsed LRC lines (time-sorted)
        anchor_threshold: Minimum combined score for anchor selection
        logprob_threshold: Minimum avg_logprob from Whisper (-0.7 = moderate confidence)
        min_anchor_ratio: Minimum anchors/GT ratio before falling back
        match_threshold: Threshold for greedy fallback
        time_weight: Time proximity weight for greedy fallback
        max_lookahead: Lookahead for greedy fallback
        phantom_threshold_ms: Max distance for phantom detection
        output_traditional: Convert output text to Traditional Chinese

    Returns:
        AlignmentResult with aligned segments and statistics.
    """
    # Phase 1: Pre-normalize all text
    w_norms = [_normalize_chinese(seg["text"].strip()) for seg in whisper_segments]
    g_norms = [_normalize_chinese(line.text) for line in gt_lines]

    # Phase 2: Extract anchors
    anchors = _extract_anchors(
        whisper_segments, gt_lines, w_norms, g_norms,
        anchor_threshold=anchor_threshold,
        logprob_threshold=logprob_threshold,
    )

    anchor_ratio = len(anchors) / len(gt_lines) if gt_lines else 0.0

    logger.info(
        "Anchor extraction: %d anchors from %d GT lines (ratio=%.2f, threshold=%.2f)",
        len(anchors), len(gt_lines), anchor_ratio, min_anchor_ratio,
    )

    # Check if GT lines have timestamps (needed for warping)
    has_timestamps = any(line.time_ms > 0 for line in gt_lines)

    # Fallback conditions
    if len(anchors) < 2 or anchor_ratio < min_anchor_ratio or not has_timestamps:
        logger.info(
            "Falling back to greedy alignment (anchors=%d, ratio=%.2f, timestamps=%s)",
            len(anchors), anchor_ratio, has_timestamps,
        )
        return _greedy_align(
            whisper_segments, gt_lines, w_norms, g_norms,
            match_threshold=match_threshold,
            time_weight=time_weight,
            max_lookahead=max_lookahead,
            output_traditional=output_traditional,
        )

    # Phase 3: Warp GT timeline
    segments = _warp_gt_lines(
        gt_lines, anchors, whisper_segments,
        output_traditional=output_traditional,
    )

    # Phase 4: Detect phantom lines
    _detect_phantoms(segments, whisper_segments, phantom_threshold_ms)

    # Compute statistics
    anchor_count = sum(1 for s in segments if s.source_type == "anchor")
    non_anchor = len(segments) - anchor_count
    confidences = [s.confidence for s in segments if s.confidence > 0]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    result = AlignmentResult(
        segments=segments,
        matched_count=anchor_count,
        unmatched_count=non_anchor,
        average_confidence=avg_confidence,
        gt_lines_used=len(segments),
        gt_lines_total=len(gt_lines),
        algorithm="anchor",
    )

    logger.info(
        "Anchor alignment complete: %d/%d anchors (avg confidence=%.2f), "
        "%d interpolated, %d extrapolated, %d phantom",
        anchor_count,
        len(gt_lines),
        avg_confidence,
        sum(1 for s in segments if s.source_type == "interpolated"),
        sum(1 for s in segments if s.source_type == "extrapolated"),
        sum(1 for s in segments if s.source_type == "phantom"),
    )

    return result


# ---------------------------------------------------------------------------
# Optional: BPM beat-snap
# ---------------------------------------------------------------------------

def snap_to_beats(
    segments: list[AlignedSegment],
    audio_path: str,
    tolerance_ms: int = 150,
) -> list[AlignedSegment]:
    """Snap segment start times to nearest musical beat.

    Uses librosa beat detection to find the beat grid, then nudges
    each segment's start_ms to the nearest beat if within tolerance.
    Makes subtitle transitions feel more musical.

    Args:
        segments: Already-aligned segments from align()
        audio_path: Path to audio file for beat detection
        tolerance_ms: Maximum ms to shift a timestamp

    Returns:
        Modified segments (in-place) with beat-snapped start_ms.
    """
    try:
        import librosa
        import numpy as np
    except ImportError:
        logger.info("librosa not installed — skipping BPM snap")
        return segments

    y, sr = librosa.load(audio_path, sr=22050)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times_ms = (librosa.frames_to_time(beat_frames, sr=sr) * 1000).astype(int)

    if len(beat_times_ms) == 0:
        logger.warning("No beats detected — skipping BPM snap")
        return segments

    snapped_count = 0
    for seg in segments:
        idx = np.searchsorted(beat_times_ms, seg.start_ms)
        candidates = []
        if idx > 0:
            candidates.append(int(beat_times_ms[idx - 1]))
        if idx < len(beat_times_ms):
            candidates.append(int(beat_times_ms[idx]))

        for beat_ms in candidates:
            if abs(beat_ms - seg.start_ms) <= tolerance_ms:
                seg.start_ms = beat_ms
                snapped_count += 1
                break

    bpm_val = float(tempo) if not hasattr(tempo, "__len__") else float(tempo[0])
    logger.info(
        "BPM snap: %d/%d segments snapped (tolerance=%dms, tempo=%.1f BPM)",
        snapped_count,
        len(segments),
        tolerance_ms,
        bpm_val,
    )

    return segments
