from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/db/leader_at_worship.db"

    # Audio processing — general
    audio_dir: Path = Path("data/audio")
    export_dir: Path = Path("data/exports")

    # Whisper — speech-to-text (mlx-whisper on Apple Silicon)
    whisper_model: str = "mlx-community/whisper-large-v3-turbo"
    whisper_language: str = "zh"
    whisper_initial_prompt: str = (
        "以下是敬拜讚美詩歌的歌詞，繁體中文。"
        "常見詞彙：哈利路亞、榮耀、恩典、救贖、十字架、寶血、聖靈、"
        "凡事包容、凡事相信、凡事盼望、凡事忍耐、愛是永不止息。"
    )

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

    # Lyrics alignment
    alignment_enabled: bool = True
    alignment_match_threshold: float = 0.55
    alignment_min_confidence: float = 0.5
    alignment_min_match_ratio: float = 0.4
    alignment_bpm_snap: bool = False  # Requires librosa (optional)
    alignment_bpm_snap_tolerance_ms: int = 150

    # Anchor-based alignment v2
    alignment_anchor_threshold: float = 0.55      # Minimum score for anchor
    alignment_logprob_threshold: float = -0.7     # Minimum avg_logprob from Whisper
    alignment_min_anchor_ratio: float = 0.4       # Anchors/GT ratio before fallback
    alignment_phantom_threshold_ms: int = 3000    # Max distance for phantom detection
    alignment_output_traditional: bool = True     # Convert output to Traditional Chinese

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    model_config = {"env_file": ".env", "env_prefix": "LAW_"}


settings = Settings()
