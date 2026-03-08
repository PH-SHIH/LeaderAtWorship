from pathlib import Path

from app.config import settings


def generate_srt(lines: list[dict], output_path: Path | None = None) -> str:
    """Generate SRT format subtitle content from timestamped lines."""
    parts = []
    for i, line in enumerate(lines, 1):
        start = _ms_to_srt_time(line["start_ms"])
        end = _ms_to_srt_time(line["end_ms"])
        text = line["text"]
        if "text_secondary" in line and line["text_secondary"]:
            text += f"\n{line['text_secondary']}"
        parts.append(f"{i}\n{start} --> {end}\n{text}\n")

    content = "\n".join(parts)

    if output_path:
        settings.export_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

    return content


def generate_vtt(lines: list[dict], output_path: Path | None = None) -> str:
    """Generate WebVTT format subtitle content."""
    parts = ["WEBVTT\n"]
    for i, line in enumerate(lines, 1):
        start = _ms_to_vtt_time(line["start_ms"])
        end = _ms_to_vtt_time(line["end_ms"])
        text = line["text"]
        if "text_secondary" in line and line["text_secondary"]:
            text += f"\n{line['text_secondary']}"
        parts.append(f"{i}\n{start} --> {end}\n{text}\n")

    content = "\n".join(parts)

    if output_path:
        settings.export_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

    return content


def _ms_to_srt_time(ms: int) -> str:
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    ms_rem = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms_rem:03d}"


def _ms_to_vtt_time(ms: int) -> str:
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    ms_rem = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms_rem:03d}"
