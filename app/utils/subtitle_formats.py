import re


def parse_srt(content: str) -> list[dict]:
    """Parse SRT subtitle content into timestamped segments."""
    segments = []
    blocks = re.split(r"\n\n+", content.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        time_match = re.match(
            r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})",
            lines[1],
        )
        if not time_match:
            continue

        start_ms = _srt_time_to_ms(time_match.group(1))
        end_ms = _srt_time_to_ms(time_match.group(2))
        text = "\n".join(lines[2:])

        segments.append({"start_ms": start_ms, "end_ms": end_ms, "text": text})

    return segments


def _srt_time_to_ms(time_str: str) -> int:
    time_str = time_str.replace(",", ".")
    parts = time_str.split(":")
    h, m = int(parts[0]), int(parts[1])
    s_parts = parts[2].split(".")
    s, ms = int(s_parts[0]), int(s_parts[1])
    return h * 3600000 + m * 60000 + s * 1000 + ms
