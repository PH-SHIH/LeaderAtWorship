"""Check availability of optional ML dependencies."""


class MLDependencyError(RuntimeError):
    """Raised when a required ML dependency is not installed."""

    pass


def check_demucs() -> bool:
    """Check if Demucs (vocal separation) is available."""
    try:
        import demucs  # noqa: F401

        return True
    except ImportError:
        return False


def check_whisper() -> bool:
    """Check if mlx-whisper (speech-to-text on Apple Silicon) is available."""
    try:
        import mlx_whisper  # noqa: F401

        return True
    except ImportError:
        return False
