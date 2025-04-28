class BotError(Exception):
    """Базовый класс для ошибок в боте с текстом для пользователя."""

    def __init__(self, message: str, user_friendly: str | None = None):
        super().__init__(message)
        self.user_friendly = user_friendly or "Произошла ошибка. Попробуйте позже."  # noqa: D401


class StorageError(BotError):
    """Ошибки работы с хранилищем."""


class LLMError(BotError):
    """Ошибки взаимодействия с LLM (OpenAI)."""


class RateLimitExceeded(BotError):
    """Превышен лимит запросов.""" 