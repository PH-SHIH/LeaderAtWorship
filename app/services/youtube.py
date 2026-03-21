import asyncio
from dataclasses import dataclass
from pathlib import Path

from app.config import settings


@dataclass
class DownloadResult:
    """Result of a YouTube audio download with video metadata."""

    audio_path: Path
    title: str
    artist: str | None
    duration_seconds: int | None
    video_id: str


async def download_audio(url: str) -> DownloadResult:
    """Download audio from YouTube URL as WAV for ML processing.

    Returns a DownloadResult containing the audio file path and video metadata.
    """
    import yt_dlp

    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(settings.audio_dir / "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }

    # Auto-detect ffmpeg location if not on PATH
    import shutil

    if not shutil.which("ffmpeg"):
        for candidate in ["/opt/homebrew/bin", "/usr/local/bin"]:
            if Path(candidate, "ffmpeg").exists():
                ydl_opts["ffmpeg_location"] = candidate
                break

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return DownloadResult(
                audio_path=settings.audio_dir / f"{info['id']}.wav",
                title=info.get("title", "Unknown"),
                artist=info.get("artist") or info.get("uploader"),
                duration_seconds=info.get("duration"),
                video_id=info["id"],
            )

    return await asyncio.to_thread(_download)
