from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/db/leader_at_worship.db"

    # Audio processing — general
    audio_dir: Path = Path("data/audio")
    export_dir: Path = Path("data/exports")
    whisper_model: str = "turbo"

    # Demucs — vocal separation
    # htdemucs: fast & good quality (recommended)
    # htdemucs_ft: 4x slower, ~1-3% better quality
    # mdx_extra: fastest, slightly lower quality
    demucs_model: str = "htdemucs"
    demucs_device: str = "cpu"  # cpu recommended for Apple Silicon (MPS unreliable)
    demucs_shifts: int = 1  # equivariance shifts: 1=fast, 2-4=better quality, 10=best
    demucs_segment: int = 10  # chunk size in seconds
    demucs_overlap: float = 0.1  # chunk overlap ratio (0.1=fast, 0.25=quality)
    demucs_jobs: int = 8  # parallel workers (match M3 Max performance core count)

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    model_config = {"env_file": ".env", "env_prefix": "LAW_"}


settings = Settings()
