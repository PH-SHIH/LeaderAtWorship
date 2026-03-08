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
    """Check if OpenAI Whisper (speech-to-text) is available."""
    try:
        import whisper  # noqa: F401

        return True
    except ImportError:
        return False
