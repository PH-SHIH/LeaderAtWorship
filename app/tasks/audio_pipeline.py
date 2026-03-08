import logging
import time

from app.config import settings
from app.database import async_session_factory
from app.models.song import Song
from app.models.subtitle import SubtitleFile, SubtitleLine
from app.services import youtube, separator, transcriber
from app.services.subtitle_generator import generate_srt
from app.tasks.task_store import task_store
from app.utils.deps_check import MLDependencyError, check_demucs, check_whisper

logger = logging.getLogger(__name__)


def _fmt_elapsed(seconds: float) -> str:
    """Format elapsed time for display."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s}s"


async def run_audio_pipeline(
    task_id: str, youtube_url: str, whisper_model: str | None = None
):
    """Orchestrate: download -> separate -> transcribe -> generate subtitle -> persist to DB.

    Args:
        task_id: UUID string for tracking progress in task_store.
        youtube_url: YouTube video URL to process.
        whisper_model: Optional whisper model name override (unused for now).
    """
    pipeline_start = time.perf_counter()
    timings: dict[str, float] = {}

    try:
        # Step 1: Download audio from YouTube
        task_store[task_id].update({"status": "downloading", "progress": 10})
        t0 = time.perf_counter()
        dl_result = await youtube.download_audio(youtube_url)
        timings["download"] = time.perf_counter() - t0
        task_store[task_id].update({"video_title": dl_result.title, "progress": 25})
        logger.info(
            "Downloaded: %s (%s) in %s",
            dl_result.title,
            dl_result.video_id,
            _fmt_elapsed(timings["download"]),
        )

        # Step 2: Vocal separation (optional — skip if Demucs not installed)
        audio_for_transcription = dl_result.audio_path
        vocals_audio_path = None
        if check_demucs():
            task_store[task_id].update({"status": "separating", "progress": 30})
            t0 = time.perf_counter()
            vocals_path, _ = await separator.separate(dl_result.audio_path)
            timings["separation"] = time.perf_counter() - t0
            audio_for_transcription = vocals_path
            vocals_audio_path = vocals_path
            task_store[task_id].update({"progress": 55})
            logger.info("Vocal separation complete in %s", _fmt_elapsed(timings["separation"]))
        else:
            logger.warning("Demucs not installed — skipping vocal separation")
            timings["separation"] = 0
            task_store[task_id].update(
                {
                    "status": "separating",
                    "progress": 55,
                    "detail": "跳過人聲分離（Demucs 未安裝）",
                }
            )

        # Step 3: Transcription (required — fail if mlx-whisper not installed)
        if not check_whisper():
            raise MLDependencyError(
                "mlx-whisper 未安裝。請執行: pip install mlx-whisper"
            )
        task_store[task_id].update({"status": "transcribing", "progress": 60})
        t0 = time.perf_counter()
        segments = await transcriber.transcribe(audio_for_transcription)
        timings["transcription"] = time.perf_counter() - t0
        task_store[task_id].update({"progress": 85})
        logger.info(
            "Transcription complete: %d segments in %s",
            len(segments),
            _fmt_elapsed(timings["transcription"]),
        )

        # Step 4: Generate SRT file
        task_store[task_id].update({"status": "generating", "progress": 90})
        srt_filename = f"{dl_result.video_id}.srt"
        output_path = settings.export_dir / srt_filename
        generate_srt(segments, output_path)
        logger.info("SRT file generated: %s", output_path)

        # Step 5: Persist results to database
        task_store[task_id].update({"status": "saving", "progress": 95})
        async with async_session_factory() as session:
            async with session.begin():
                song = Song(
                    title=dl_result.title,
                    artist=dl_result.artist,
                    audio_path=str(dl_result.audio_path),
                    vocals_path=str(vocals_audio_path) if vocals_audio_path else None,
                )
                session.add(song)
                await session.flush()

                subtitle_file = SubtitleFile(
                    song_id=song.id,
                    filename=srt_filename,
                    format="srt",
                    source="whisper",
                    file_path=str(output_path),
                )
                session.add(subtitle_file)
                await session.flush()

                for i, seg in enumerate(segments):
                    line = SubtitleLine(
                        subtitle_file_id=subtitle_file.id,
                        index=i + 1,
                        start_ms=seg["start_ms"],
                        end_ms=seg["end_ms"],
                        text=seg["text"],
                    )
                    session.add(line)

            result_id = subtitle_file.id
            song_id = song.id

        total_elapsed = time.perf_counter() - pipeline_start
        timings["total"] = total_elapsed

        logger.info(
            "Pipeline complete for '%s': total=%s (download=%s, separation=%s, transcription=%s) "
            "→ Song #%d, SubtitleFile #%d (%d lines)",
            dl_result.title,
            _fmt_elapsed(total_elapsed),
            _fmt_elapsed(timings["download"]),
            _fmt_elapsed(timings["separation"]),
            _fmt_elapsed(timings["transcription"]),
            song_id,
            result_id,
            len(segments),
        )

        task_store[task_id].update(
            {
                "status": "completed",
                "progress": 100,
                "result_id": result_id,
                "song_id": song_id,
            }
        )

    except Exception as e:
        total_elapsed = time.perf_counter() - pipeline_start
        logger.exception(
            "Audio pipeline failed for task %s after %s: %s",
            task_id,
            _fmt_elapsed(total_elapsed),
            e,
        )
        task_store[task_id].update({"status": "failed", "error": str(e)})
