import asyncio
import logging
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from app.config import settings
from app.utils.deps_check import MLDependencyError, check_demucs

logger = logging.getLogger(__name__)


def _detect_device() -> str:
    """Auto-detect the best device for Demucs on the current platform.

    Priority: user override (settings) > MPS (Apple Silicon) > CPU.
    """
    configured = settings.demucs_device
    if configured != "auto":
        return configured

    if platform.machine() == "arm64" and sys.platform == "darwin":
        try:
            import torch
            if torch.backends.mps.is_available():
                logger.info("Apple Silicon MPS detected — using mps device")
                return "mps"
        except Exception:
            pass
        logger.info("Apple Silicon detected but MPS unavailable — using cpu")
    return "cpu"


def _optimal_jobs() -> int:
    """Return optimal job count based on platform."""
    if settings.demucs_jobs > 0:
        return settings.demucs_jobs
    # Auto: use performance core count (Apple Silicon) or half of CPU count
    try:
        count = os.cpu_count() or 4
        return max(1, count // 2)
    except Exception:
        return 4


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

    stem_name = audio_path.stem
    model_name = settings.demucs_model

    # Check if separation already done (any model) — reuse existing results
    vocals, no_vocals = _find_existing_output(output_dir, stem_name, model_name)
    if vocals and vocals.exists():
        logger.info("Reusing existing separation: %s", vocals)
        return vocals, no_vocals

    device = _detect_device()
    jobs = _optimal_jobs()

    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems",
        "vocals",
        "-n",
        model_name,
        "-d",
        device,
        "--shifts",
        str(settings.demucs_shifts),
        "--segment",
        str(settings.demucs_segment),
        "--overlap",
        str(settings.demucs_overlap),
        "-j",
        str(jobs),
        "-o",
        str(output_dir),
        str(audio_path),
    ]

    logger.info(
        "Demucs: model=%s device=%s shifts=%d segment=%ds overlap=%.2f jobs=%d",
        model_name,
        device,
        settings.demucs_shifts,
        settings.demucs_segment,
        settings.demucs_overlap,
        jobs,
    )

    def _run_demucs():
        env = {
            **os.environ,
            # Graceful MPS fallback for ops not yet supported on MPS
            "PYTORCH_ENABLE_MPS_FALLBACK": "1",
            # Prevent MPS from pre-allocating all GPU memory
            "PYTORCH_MPS_HIGH_WATERMARK_RATIO": "0.0",
            # Optimal thread count for Apple Silicon performance cores
            "OMP_NUM_THREADS": str(jobs),
            "MKL_NUM_THREADS": str(jobs),
        }
        t0 = time.perf_counter()
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
        except subprocess.CalledProcessError as e:
            # Extract last meaningful lines from stderr for user-facing error
            stderr_lines = (e.stderr or "").strip().splitlines()
            # Find the actual error — skip traceback preamble
            error_summary = ""
            for line in reversed(stderr_lines):
                stripped = line.strip()
                if stripped and not stripped.startswith("Traceback") and not stripped.startswith("File "):
                    error_summary = stripped
                    break
            if not error_summary and stderr_lines:
                error_summary = stderr_lines[-1]
            logger.error("Demucs stderr:\n%s", e.stderr)
            raise RuntimeError(
                f"Demucs 人聲分離失敗 — {error_summary or '未知錯誤'}"
            ) from e
        elapsed = time.perf_counter() - t0
        logger.info("Demucs finished in %.1fs", elapsed)
        if result.stderr:
            for line in result.stderr.strip().splitlines()[-5:]:
                logger.debug("demucs: %s", line)

    await asyncio.to_thread(_run_demucs)

    vocals = output_dir / model_name / stem_name / "vocals.wav"
    no_vocals = output_dir / model_name / stem_name / "no_vocals.wav"

    return vocals, no_vocals


def _find_existing_output(
    output_dir: Path, stem_name: str, preferred_model: str
) -> tuple[Path | None, Path | None]:
    """Look for existing separation results, preferring the configured model."""
    # Try configured model first
    vocals = output_dir / preferred_model / stem_name / "vocals.wav"
    if vocals.exists():
        no_vocals = output_dir / preferred_model / stem_name / "no_vocals.wav"
        return vocals, no_vocals

    # Fall back to any model that has results for this stem
    if output_dir.exists():
        for model_dir in output_dir.iterdir():
            if model_dir.is_dir():
                v = model_dir / stem_name / "vocals.wav"
                if v.exists():
                    nv = model_dir / stem_name / "no_vocals.wav"
                    logger.info("Found existing separation from model '%s'", model_dir.name)
                    return v, nv

    return None, None
