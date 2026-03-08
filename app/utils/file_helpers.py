from pathlib import Path

from app.config import settings


def ensure_data_dirs():
    """Ensure all runtime data directories exist."""
    for dir_path in [settings.audio_dir, settings.export_dir, Path("data/db"), Path("data/models")]:
        dir_path.mkdir(parents=True, exist_ok=True)
