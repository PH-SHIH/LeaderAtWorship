import asyncio
import logging
from pathlib import Path

from app.config import settings
from app.utils.deps_check import MLDependencyError, check_whisper

logger = logging.getLogger(__name__)


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

    return await asyncio.to_thread(_transcribe)
