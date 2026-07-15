class AIBusyError(Exception):
    """Raised after a transient AI 429/timeout retry is exhausted."""
