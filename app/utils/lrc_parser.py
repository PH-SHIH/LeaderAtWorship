"""Parse LRC (Lyrics) format into timestamped lines."""

import re
from dataclasses import dataclass


@dataclass
class LrcLine:
    """A single LRC line with timestamp and text."""

    time_ms: int
    text: str


def parse_lrc(content: str) -> list[LrcLine]:
    """Parse LRC content into a list of LrcLine objects.

    Handles standard LRC format:
        [mm:ss.xx] lyrics text
        [mm:ss.xxx] lyrics text

    Also handles:
        - Metadata tags like [ar:], [ti:], [al:] (skipped)
        - Multiple timestamps per line: [00:30.00][01:15.00] repeated line
        - Empty lines (skipped)

    Returns lines sorted by time_ms.
    """
    lines: list[LrcLine] = []
    timestamp_re = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\]")
    metadata_re = re.compile(r"^\[\w+:.*\]$")

    for raw_line in content.strip().splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        # Skip pure metadata lines like [ar:Artist Name]
        if metadata_re.match(raw_line) and not timestamp_re.search(raw_line):
            continue

        # Find all timestamps on this line
        timestamps: list[int] = []
        for match in timestamp_re.finditer(raw_line):
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            frac = match.group(3)
            # Normalize: .xx → ×10ms, .xxx → ms
            ms = int(frac) * 10 if len(frac) == 2 else int(frac)
            time_ms = minutes * 60_000 + seconds * 1_000 + ms
            timestamps.append(time_ms)

        if not timestamps:
            continue

        # Extract text after all timestamp tags
        text = timestamp_re.sub("", raw_line).strip()
        if not text:
            continue

        # One LrcLine per timestamp (handles repeated choruses)
        for ts in timestamps:
            lines.append(LrcLine(time_ms=ts, text=text))

    lines.sort(key=lambda l: l.time_ms)
    return lines
