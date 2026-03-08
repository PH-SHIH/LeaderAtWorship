"""Fetch synced lyrics (LRC format) from online providers."""

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
    provider: str  # e.g. "syncedlyrics"
    raw_lrc: str  # Original LRC content for storage
    has_timestamps: bool


def _clean_youtube_title(title: str) -> str:
    """Strip common YouTube noise from a video title.

    Examples:
        "林佳蓉 許淑絹-愛的真諦 (官方完整版MV)" -> "林佳蓉 許淑絹-愛的真諦"
        "愛的真諦 Official MV [HD]"              -> "愛的真諦"
    """
    # Remove parenthetical notes: (官方MV), (Official MV), etc.
    title = re.sub(
        r"\s*[(\（][^)）]*(?:MV|mv|版|HD|hd|lyric|Lyric|LYRIC|video|Video|歌詞)[^)）]*[)\）]",
        "", title,
    )
    # Remove bracket notes: [HD], [Official], etc.
    title = re.sub(
        r"\s*\[[^\]]*(?:MV|HD|hd|Official|official|4K|lyric|Lyric)[^\]]*\]",
        "", title,
    )
    # Remove trailing pipe sections: "| 字幕版", "| Official"
    title = re.sub(r"\s*[|｜].*$", "", title)
    # Remove common suffixes
    title = re.sub(
        r"\s*(?:官方|完整版|Official|official|MV|mv|Music Video|music video|HD|4K)\s*$",
        "", title,
    )
    return title.strip()


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
        # Only split if left side looks like an artist name (not too long)
        left, right = parts[0].strip(), parts[1].strip()
        if left and right and len(left) < 30:
            return left, right

    return None, title


def _build_search_terms(title: str, artist: str | None) -> list[str]:
    """Build an ordered list of search term variations to try.

    Strategies (most specific to least):
    1. song_name + title_artist  (extracted from "Artist-Song" pattern)
    2. song_name + channel_artist
    3. clean title as-is
    4. song_name alone
    5. Repeat key terms in simplified Chinese
    """
    from hanziconv import HanziConv

    clean_title = _clean_youtube_title(title)
    title_artist, song_name = _split_artist_song(clean_title)

    terms = []

    # Strategy 1: song_name + artist extracted from title
    if title_artist:
        terms.append(f"{song_name} {title_artist}")

    # Strategy 2: song_name + YouTube channel artist
    if artist and artist != title_artist:
        terms.append(f"{song_name} {artist}")

    # Strategy 3: clean title as-is (if it's different from song_name)
    if clean_title != song_name:
        terms.append(clean_title)

    # Strategy 4: song_name only
    terms.append(song_name)

    # Interleave simplified Chinese versions right after each term.
    # Many lyrics databases (especially NetEase) index in simplified Chinese,
    # so searching simplified first avoids slow timeouts on providers that
    # don't have traditional Chinese results.
    interleaved = []
    for t in terms:
        simplified = HanziConv.toSimplified(t)
        if simplified != t:
            # Put simplified first (higher hit rate on Chinese lyrics DBs)
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


async def fetch_lyrics(title: str, artist: str | None = None) -> FetchResult | None:
    """Search for synced lyrics using syncedlyrics library.

    Tries multiple search strategies with progressively simpler terms.
    Also tries simplified Chinese conversions since many lyrics databases
    index in simplified Chinese.

    Returns None if no lyrics found from any provider.
    """

    def _fetch():
        import syncedlyrics

        search_terms = _build_search_terms(title, artist)

        for search_term in search_terms:
            logger.info("Searching lyrics for: %s", search_term)
            lrc_text = syncedlyrics.search(search_term, synced_only=True)
            if lrc_text:
                logger.info("Found lyrics with search term: %s", search_term)
                return lrc_text

        return None

    lrc_text = await asyncio.to_thread(_fetch)

    if not lrc_text:
        logger.info("No synced lyrics found after trying all search strategies")
        return None

    lines = parse_lrc(lrc_text)
    if not lines:
        logger.warning("LRC parsed but yielded no lines")
        return None

    has_timestamps = any(line.time_ms > 0 for line in lines)

    logger.info(
        "Found %d lyrics lines (timestamps=%s)",
        len(lines),
        has_timestamps,
    )

    return FetchResult(
        lines=lines,
        provider="syncedlyrics",
        raw_lrc=lrc_text,
        has_timestamps=has_timestamps,
    )
