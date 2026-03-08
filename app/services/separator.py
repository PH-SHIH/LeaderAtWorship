import asyncio
import logging
import subprocess
import time
from pathlib import Path

from app.config import settings
from app.utils.deps_check import MLDependencyError, check_demucs

logger = logging.getLogger(__name__)


async def separate(audio_path: Path) -> tuple[Path, Path]:
    """Separate vocals using Demucs, optimized for Apple Silicon.

    Uses settings for device, parallelism, and quality tuning.
    Returns (vocals_path, accompaniment_path).
    Raises MLDependencyError if Demucs is not installed.
    """
    if not check_demucs():
        raise MLDependencyError(
            "Demucs is not installed. Install it with: pip install 'leader-at-worship[ml]'"
        )

    output_dir = audio_path.parent / "separated"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python",
        "-m",
        "demucs",
        "--two-stems",
        "vocals",
        "-n",
        settings.demucs_model,
        "-d",
        settings.demucs_device,
        "--shifts",
        str(settings.demucs_shifts),
        "--segment",
        str(settings.demucs_segment),
        "--overlap",
        str(settings.demucs_overlap),
        "-j",
        str(settings.demucs_jobs),
        "-o",
        str(output_dir),
        str(audio_path),
    ]

    logger.info(
        "Demucs: model=%s device=%s shifts=%d segment=%ds overlap=%.2f jobs=%d",
        settings.demucs_model,
        settings.demucs_device,
        settings.demucs_shifts,
        settings.demucs_segment,
        settings.demucs_overlap,
        settings.demucs_jobs,
    )

    def _run_demucs():
        env = {
            **__import__("os").environ,
            # Graceful MPS fallback (in case user sets device=mps)
            "PYTORCH_ENABLE_MPS_FALLBACK": "1",
            # Optimal thread count for M3 Max performance cores
            "OMP_NUM_THREADS": str(settings.demucs_jobs),
        }
        t0 = time.perf_counter()
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        elapsed = time.perf_counter() - t0
        logger.info("Demucs finished in %.1fs", elapsed)
        if result.stderr:
            for line in result.stderr.strip().splitlines()[-5:]:
                logger.debug("demucs: %s", line)

    await asyncio.to_thread(_run_demucs)

    stem_name = audio_path.stem
    model_name = settings.demucs_model
    vocals = output_dir / model_name / stem_name / "vocals.wav"
    no_vocals = output_dir / model_name / stem_name / "no_vocals.wav"

    return vocals, no_vocals
