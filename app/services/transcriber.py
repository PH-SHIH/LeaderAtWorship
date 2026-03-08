import asyncio
from pathlib import Path

from app.config import settings
from app.utils.deps_check import MLDependencyError, check_whisper

_model = None


def get_model():
    """Load and cache the Whisper model (singleton)."""
    global _model
    if _model is None:
        if not check_whisper():
            raise MLDependencyError(
                "Whisper is not installed. Install it with: pip install 'leader-at-worship[ml]'"
            )
        import whisper

        _model = whisper.load_model(settings.whisper_model)
    return _model


async def transcribe(audio_path: Path) -> list[dict]:
    """Transcribe audio and return timestamped segments.

    Each segment is a dict with keys: start_ms, end_ms, text.
    Raises MLDependencyError if Whisper is not installed.
    """

    def _transcribe():
        model = get_model()
        result = model.transcribe(
            str(audio_path),
            word_timestamps=True,
            language=None,  # Auto-detect
        )
        return [
            {
                "start_ms": int(seg["start"] * 1000),
                "end_ms": int(seg["end"] * 1000),
                "text": seg["text"].strip(),
            }
            for seg in result["segments"]
        ]

    return await asyncio.to_thread(_transcribe)
