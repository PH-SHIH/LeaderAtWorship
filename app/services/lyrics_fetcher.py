"""Fetch synced lyrics (LRC format) from online providers.

Multi-strategy search with Chinese-optimized provider ordering:
1. syncedlyrics (Musixmatch, NetEase, Lrclib, etc.)
2. LRCLIB direct REST API (high-quality community database)
3. Fallback to plain (unsynced) lyrics when synced unavailable

Search term generation splits multi-artist names and interleaves
simplified/traditional Chinese variants for maximum coverage.
"""

import asyncio
import logging
import re
from dataclasses import dataclass

from app.utils.lrc_parser import LrcLine, parse_lrc

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result of a lyrics fetch attempt."""

    lines: list[LrcLine]
    provider: str  # e.g. "syncedlyrics", "lrclib"
    raw_lrc: str  # Original LRC content for storage
    has_timestamps: bool


def _clean_youtube_title(title: str) -> str:
    """Strip common YouTube noise from a video title.

    Examples:
        "林佳蓉 許淑絹-愛的真諦 (官方完整版MV)" -> "林佳蓉 許淑絹-愛的真諦"
        "愛的真諦 Official MV [HD]"              -> "愛的真諦"
        "Amazing Grace ( with Lyrics ) / 奇異恩典( 中文歌詞 ) By Hayley Westenra / 海莉薇思特娜"
            -> "Amazing Grace / 奇異恩典"
    """
    # Remove parenthetical notes: (官方MV), (Official MV), (with Lyrics), (中文歌詞), etc.
    title = re.sub(
        r"\s*[(\（][^)）]*(?:MV|mv|版|HD|hd|lyric|Lyric|LYRIC|video|Video|歌詞|Lyrics|lyrics|with)[^)）]*[)\）]",
        "", title,
    )
    # Remove bracket notes: [HD], [Official], etc.
    title = re.sub(
        r"\s*\[[^\]]*(?:MV|HD|hd|Official|official|4K|lyric|Lyric)[^\]]*\]",
        "", title,
    )
    # Remove trailing pipe sections: "| 字幕版", "| Official"
    title = re.sub(r"\s*[|｜].*$", "", title)
    # Remove "By Artist / Artist" suffix (common in bilingual titles)
    title = re.sub(r"\s+[Bb]y\s+.*$", "", title)
    # Remove common suffixes
    title = re.sub(
        r"\s*(?:官方|完整版|Official|official|MV|mv|Music Video|music video|HD|4K)\s*$",
        "", title,
    )
    return title.strip()


def _extract_by_artist(title: str) -> str | None:
    """Extract artist name from 'By Artist / ...' pattern in raw title."""
    m = re.search(r"\s+[Bb]y\s+(.+?)(?:\s*/\s*|\s*$)", title)
    if m:
        return m.group(1).strip()
    return None


def _split_slash_parts(title: str) -> list[str]:
    """Split bilingual titles on '/' separator.

    "Amazing Grace / 奇異恩典" → ["Amazing Grace", "奇異恩典"]
    """
    parts = [p.strip() for p in title.split("/") if p.strip()]
    return parts if len(parts) > 1 else [title]


def _split_artist_song(title: str) -> tuple[str | None, str]:
    """Split "Artist - Song Name" into (artist, song_name).

    Handles common separators: " - ", "-", "–", "—".
    Returns (None, title) if no separator found.
    """
    for sep in [" - ", " – ", " — "]:
        if sep in title:
            parts = title.split(sep, 1)
            return parts[0].strip(), parts[-1].strip()

    # Try single dash (common in Chinese titles like "林佳蓉-愛的真諦")
    if "-" in title:
        parts = title.split("-", 1)
        left, right = parts[0].strip(), parts[1].strip()
        if left and right and len(left) < 30:
            return left, right

    return None, title


def _split_multi_artists(artist_str: str) -> list[str]:
    """Split multi-artist string into individual artist names.

    "林佳蓉 許淑絹" → ["林佳蓉 許淑絹", "林佳蓉", "許淑絹"]
    "約書亞樂團" → ["約書亞樂團"]
    "Amy & John" → ["Amy & John", "Amy", "John"]
    """
    results = [artist_str]

    # Split on common separators — try structured patterns first, then CJK spaces
    # Only split if both parts look like names (2+ chars each)
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", artist_str))
    # Space-split only for CJK text (Chinese names like "林佳蓉 許淑絹")
    # Western names like "Hayley Westenra" should NOT be split on spaces
    separators = [r"\s*(?:feat\.?|ft\.?)\s*", r"\s*[&＆×]\s*"]
    if has_cjk:
        separators.append(r"\s+")
    for sep_pattern in separators:
        parts = re.split(sep_pattern, artist_str, flags=re.IGNORECASE)
        if len(parts) >= 2 and all(len(p.strip()) >= 2 for p in parts):
            for p in parts:
                p = p.strip()
                if p and p != artist_str:
                    results.append(p)
            break  # Only split on first matching separator

    return results


def _build_search_terms(title: str, artist: str | None) -> list[str]:
    """Build an ordered list of search term variations to try.

    Strategies (most specific to least):
    1. song_name + full artist string
    2. song_name + individual artists (split from multi-artist)
    3. song_name + channel_artist
    4. song_name + "By" artist
    5. Individual slash parts (bilingual titles)
    6. clean title as-is
    7. song_name alone
    + Interleave simplified Chinese versions for each term
    """
    from hanziconv import HanziConv

    by_artist = _extract_by_artist(title)
    clean_title = _clean_youtube_title(title)
    title_artist, song_name = _split_artist_song(clean_title)

    terms = []

    # Strategy 1 & 2: song_name + artists (full then individual)
    if title_artist:
        terms.append(f"{song_name} {title_artist}")
        # Split multi-artist and try each individually
        for individual in _split_multi_artists(title_artist):
            term = f"{song_name} {individual}"
            if term not in terms:
                terms.append(term)

    # Strategy 3: song_name + YouTube channel artist
    if artist and artist != title_artist:
        channel_clean = artist.split("/")[0].strip() if "/" in artist else artist
        terms.append(f"{song_name} {channel_clean}")

    # Strategy 4: song_name + "By" artist from raw title
    if by_artist and by_artist != title_artist and by_artist != artist:
        terms.append(f"{song_name} {by_artist}")

    # Strategy 5: Individual slash parts (bilingual titles)
    slash_parts = _split_slash_parts(clean_title)
    if len(slash_parts) > 1:
        for part in slash_parts:
            part_artist, part_song = _split_artist_song(part)
            if part_artist:
                terms.append(f"{part_song} {part_artist}")
            else:
                terms.append(part)
            if by_artist:
                terms.append(f"{part} {by_artist}")

    # Strategy 6: clean title as-is (if different from song_name)
    if clean_title != song_name:
        terms.append(clean_title)

    # Strategy 7: song_name only
    terms.append(song_name)

    # Interleave simplified Chinese versions right after each term.
    interleaved = []
    for t in terms:
        simplified = HanziConv.toSimplified(t)
        if simplified != t:
            interleaved.append(simplified)
        interleaved.append(t)
    terms = interleaved

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    return unique


# ---------------------------------------------------------------------------
# Provider: LRCLIB direct REST API
# ---------------------------------------------------------------------------

def _search_lrclib(search_term: str) -> str | None:
    """Search LRCLIB REST API directly for synced lyrics.

    LRCLIB is a community-maintained lyrics database with high-quality
    synced LRC content. Direct API access is more reliable than going
    through the syncedlyrics wrapper.
    """
    import urllib.request
    import urllib.parse
    import json

    url = "https://lrclib.net/api/search?" + urllib.parse.urlencode({"q": search_term})

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LeaderAtWorship/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        logger.debug("LRCLIB search failed for '%s': %s", search_term, e)
        return None

    if not data:
        return None

    # Prefer results with synced lyrics
    for item in data:
        synced = item.get("syncedLyrics")
        if synced:
            logger.info(
                "LRCLIB found synced lyrics: '%s' by '%s'",
                item.get("trackName", "?"),
                item.get("artistName", "?"),
            )
            return synced

    # Fallback: return plain lyrics wrapped in a basic LRC format
    for item in data:
        plain = item.get("plainLyrics")
        if plain:
            logger.info(
                "LRCLIB found plain lyrics (no timestamps): '%s' by '%s'",
                item.get("trackName", "?"),
                item.get("artistName", "?"),
            )
            # Convert plain text to LRC with [00:00.00] timestamps
            lines = [
                f"[00:00.00]{line}"
                for line in plain.strip().splitlines()
                if line.strip()
            ]
            return "\n".join(lines)

    return None


def _get_lrclib(title: str, artist: str) -> str | None:
    """Try LRCLIB's exact match GET endpoint."""
    import urllib.request
    import urllib.parse
    import json

    params = urllib.parse.urlencode({
        "track_name": title,
        "artist_name": artist,
    })
    url = f"https://lrclib.net/api/get?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LeaderAtWorship/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            item = json.loads(resp.read().decode())
    except Exception:
        return None

    synced = item.get("syncedLyrics")
    if synced:
        logger.info("LRCLIB exact match found synced lyrics")
        return synced

    plain = item.get("plainLyrics")
    if plain:
        logger.info("LRCLIB exact match found plain lyrics")
        lines = [f"[00:00.00]{line}" for line in plain.strip().splitlines() if line.strip()]
        return "\n".join(lines)

    return None


# ---------------------------------------------------------------------------
# Provider: syncedlyrics (multi-provider wrapper)
# ---------------------------------------------------------------------------

# Provider ordering optimized for Chinese worship songs:
# NetEase: best for Chinese songs (largest Chinese lyrics DB)
# Musixmatch: good global coverage, supports translations
# Lrclib: community-maintained, high quality
# Others: additional fallbacks
_CHINESE_PROVIDER_ORDER = ["netease", "musixmatch", "lrclib", "megalobiz", "genius"]


def _search_syncedlyrics(search_term: str, synced_only: bool = True) -> str | None:
    """Search using syncedlyrics library with Chinese-optimized provider order."""
    import syncedlyrics

    try:
        result = syncedlyrics.search(
            search_term,
            synced_only=synced_only,
            providers=_CHINESE_PROVIDER_ORDER,
        )
        return result
    except Exception as e:
        logger.debug("syncedlyrics search failed for '%s': %s", search_term, e)
        return None


def _validate_lrc_content(lrc_text: str, song_name: str) -> bool:
    """Basic validation that the found LRC content is plausible for the song.

    Rejects obviously wrong results (e.g. English lyrics for a Chinese song).
    """
    if not lrc_text:
        return False

    # Extract text content (strip timestamps)
    text_only = re.sub(r"\[\d{2}:\d{2}\.\d{2,3}\]", "", lrc_text)
    text_only = text_only.strip()

    if len(text_only) < 20:
        return False

    # If song name contains CJK characters, lyrics should too
    has_cjk_title = bool(re.search(r"[\u4e00-\u9fff]", song_name))
    has_cjk_lyrics = bool(re.search(r"[\u4e00-\u9fff]", text_only))

    if has_cjk_title and not has_cjk_lyrics:
        logger.info("Rejected lyrics: CJK song title but no CJK in lyrics content")
        return False

    return True


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def fetch_lyrics(title: str, artist: str | None = None) -> FetchResult | None:
    """Search for synced lyrics using multiple providers and strategies.

    Search phases:
    1. LRCLIB direct API (fast, high quality)
    2. syncedlyrics with Chinese-optimized provider order (synced only)
    3. syncedlyrics fallback (allow plain lyrics)

    Each phase tries all search term variations before moving to the next.

    Returns None if no lyrics found from any provider.
    """

    def _fetch():
        search_terms = _build_search_terms(title, artist)
        _, song_name = _split_artist_song(_clean_youtube_title(title))

        logger.info(
            "Lyrics search: %d terms to try for '%s'",
            len(search_terms), song_name,
        )

        # Phase 1: LRCLIB direct API (fast exact match + search)
        if artist:
            lrc = _get_lrclib(song_name, artist)
            if lrc and _validate_lrc_content(lrc, song_name):
                return lrc, "lrclib"

        for term in search_terms:
            logger.info("LRCLIB search: %s", term)
            lrc = _search_lrclib(term)
            if lrc and _validate_lrc_content(lrc, song_name):
                return lrc, "lrclib"

        # Phase 2: syncedlyrics — synced only, Chinese-optimized providers
        for term in search_terms:
            logger.info("syncedlyrics search (synced): %s", term)
            lrc = _search_syncedlyrics(term, synced_only=True)
            if lrc and _validate_lrc_content(lrc, song_name):
                return lrc, "syncedlyrics"

        # Phase 3: syncedlyrics — allow plain text lyrics as last resort
        for term in search_terms:
            logger.info("syncedlyrics search (plain fallback): %s", term)
            lrc = _search_syncedlyrics(term, synced_only=False)
            if lrc and _validate_lrc_content(lrc, song_name):
                return lrc, "syncedlyrics-plain"

        return None, None

    lrc_text, provider = await asyncio.to_thread(_fetch)

    if not lrc_text:
        logger.info("No lyrics found after trying all strategies and providers")
        return None

    lines = parse_lrc(lrc_text)
    if not lines:
        logger.warning("LRC parsed but yielded no lines")
        return None

    has_timestamps = any(line.time_ms > 0 for line in lines)

    logger.info(
        "Found %d lyrics lines via %s (timestamps=%s)",
        len(lines), provider, has_timestamps,
    )

    return FetchResult(
        lines=lines,
        provider=provider or "unknown",
        raw_lrc=lrc_text,
        has_timestamps=has_timestamps,
    )
