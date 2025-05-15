class BotError(Exception):
    """Base class for bot errors with a user-friendly message."""

    def __init__(self, message: str, user_friendly: str | None = None):
        """
        Initialize the BotError.

        Args:
            message: The internal error message.
            user_friendly: A user-friendly message to display.
        """
        super().__init__(message)
        self.user_friendly = (
            user_friendly or "An error occurred. Please try again later."
        )  # noqa: D401


class StorageError(BotError):
    """Errors related to data storage operations."""


class LLMError(BotError):
    """Errors related to interaction with the LLM (OpenAI)."""


class RateLimitExceeded(BotError):
    """Error raised when a rate limit is exceeded."""
