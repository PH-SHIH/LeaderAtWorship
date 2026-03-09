import asyncio
import logging
import re
from collections import Counter
from pathlib import Path

from app.config import settings
from app.utils.deps_check import MLDependencyError, check_whisper

logger = logging.getLogger(__name__)


def _is_hallucination(text: str, duration_ms: int) -> bool:
    """Detect common Whisper hallucination patterns.

    Patterns:
    1. Repeated single character (e.g. "兄兄兄兄兄兄...")
    2. Abnormally long segment with very repetitive content
    3. YouTube-specific hallucinations (subscribe/like prompts)
    """
    stripped = text.strip()
    if not stripped:
        return False

    # Pattern 1: Single character repeated many times (e.g. "兄兄兄兄兄...")
    # Remove all whitespace/punctuation, check if dominated by one char
    chars_only = re.sub(r"\s+", "", stripped)
    if len(chars_only) >= 6:
        counter = Counter(chars_only)
        most_common_char, most_common_count = counter.most_common(1)[0]
        if most_common_count / len(chars_only) > 0.7:
            logger.info(
                "Hallucination detected (repeated char '%s' x%d): %s",
                most_common_char, most_common_count, stripped[:50],
            )
            return True

    # Pattern 2: Abnormally long segment (>15s) — likely music/silence hallucination
    if duration_ms > 15000 and len(chars_only) > 20:
        logger.info(
            "Hallucination detected (long segment %dms): %s",
            duration_ms, stripped[:50],
        )
        return True

    # Pattern 3: YouTube outro hallucinations
    youtube_patterns = [
        r"(?:点赞|订阅|转发|打赏|支持|关注|留言|分享).*(?:点赞|订阅|转发|打赏|支持|关注|留言|分享)",
        r"(?:subscribe|like|share|comment).*(?:subscribe|like|share|comment)",
    ]
    for pattern in youtube_patterns:
        if re.search(pattern, stripped, re.IGNORECASE):
            logger.info("Hallucination detected (YouTube outro): %s", stripped[:50])
            return True

    return False


def _filter_hallucinations(segments: list[dict]) -> list[dict]:
    """Remove hallucinated segments from Whisper output."""
    filtered = []
    removed = 0
    for seg in segments:
        duration_ms = seg["end_ms"] - seg["start_ms"]
        if _is_hallucination(seg["text"], duration_ms):
            removed += 1
            continue
        filtered.append(seg)

    if removed > 0:
        logger.info("Filtered %d hallucinated segments (kept %d)", removed, len(filtered))
    return filtered


async def transcribe(audio_path: Path) -> list[dict]:
    """Transcribe audio using mlx-whisper and return timestamped segments.

    Uses mlx-community/whisper-large-v3-turbo by default for fast, high-quality
    transcription on Apple Silicon. Configured via settings:
      - whisper_model: HuggingFace repo or local path
      - whisper_language: target language code (default "zh")
      - whisper_initial_prompt: vocabulary hints for better accuracy

    Each segment is a dict with keys: start_ms, end_ms, text.
    Raises MLDependencyError if mlx-whisper is not installed.
    """
    if not check_whisper():
        raise MLDependencyError(
            "mlx-whisper 未安裝。請執行: pip install mlx-whisper"
        )

    def _transcribe():
        import mlx_whisper

        # "auto" or empty string → None (let Whisper auto-detect language)
        lang = settings.whisper_language
        if not lang or lang.lower() == "auto":
            lang = None

        logger.info(
            "Transcribing with mlx-whisper: model=%s, language=%s",
            settings.whisper_model,
            lang or "auto-detect",
        )

        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=settings.whisper_model,
            language=lang,
            initial_prompt=settings.whisper_initial_prompt if lang in ("zh", None) else None,
            word_timestamps=True,
            condition_on_previous_text=False,  # Prevent hallucination cascading
            no_speech_threshold=0.5,
        )

        detected_lang = result.get("language", "unknown")
        logger.info("Detected language: %s, segments: %d", detected_lang, len(result["segments"]))

        return [
            {
                "start_ms": int(seg["start"] * 1000),
                "end_ms": int(seg["end"] * 1000),
                "text": seg["text"].strip(),
                "avg_logprob": seg.get("avg_logprob"),
            }
            for seg in result["segments"]
        ]

    segments = await asyncio.to_thread(_transcribe)
    return _filter_hallucinations(segments)
