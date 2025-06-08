"""Tests for core exception classes."""

import pytest

from core.exceptions import BotError, StorageError, LLMError, RateLimitExceeded


def test_bot_error_with_default_user_friendly():
    """Tests BotError with default user-friendly message."""
    error = BotError("Internal error message")

    assert str(error) == "Internal error message"
    assert error.user_friendly == "An error occurred. Please try again later."


def test_bot_error_with_custom_user_friendly():
    """Tests BotError with custom user-friendly message."""
    error = BotError("Internal error", "Custom user message")

    assert str(error) == "Internal error"
    assert error.user_friendly == "Custom user message"


def test_storage_error_inheritance():
    """Tests that StorageError inherits from BotError correctly."""
    error = StorageError("Storage failed")

    assert isinstance(error, BotError)
    assert str(error) == "Storage failed"
    assert error.user_friendly == "An error occurred. Please try again later."


def test_storage_error_with_user_friendly():
    """Tests StorageError with custom user-friendly message."""
    error = StorageError("Database connection failed", "Unable to save data")

    assert str(error) == "Database connection failed"
    assert error.user_friendly == "Unable to save data"


def test_llm_error_inheritance():
    """Tests that LLMError inherits from BotError correctly."""
    error = LLMError("OpenAI API failed")

    assert isinstance(error, BotError)
    assert str(error) == "OpenAI API failed"
    assert error.user_friendly == "An error occurred. Please try again later."


def test_llm_error_with_user_friendly():
    """Tests LLMError with custom user-friendly message."""
    error = LLMError("API rate limit", "AI service temporarily unavailable")

    assert str(error) == "API rate limit"
    assert error.user_friendly == "AI service temporarily unavailable"


def test_rate_limit_exceeded_inheritance():
    """Tests that RateLimitExceeded inherits from BotError correctly."""
    error = RateLimitExceeded("Rate limit exceeded")

    assert isinstance(error, BotError)
    assert str(error) == "Rate limit exceeded"
    assert error.user_friendly == "An error occurred. Please try again later."


def test_rate_limit_exceeded_with_user_friendly():
    """Tests RateLimitExceeded with custom user-friendly message."""
    error = RateLimitExceeded("Too many requests", "Please wait before trying again")

    assert str(error) == "Too many requests"
    assert error.user_friendly == "Please wait before trying again"


def test_exception_raising():
    """Tests that exceptions can be raised and caught properly."""
    with pytest.raises(BotError) as exc_info:
        raise BotError("Test error")

    assert str(exc_info.value) == "Test error"

    with pytest.raises(StorageError) as exc_info:
        raise StorageError("Storage test error")

    assert str(exc_info.value) == "Storage test error"

    with pytest.raises(LLMError) as exc_info:
        raise LLMError("LLM test error")

    assert str(exc_info.value) == "LLM test error"

    with pytest.raises(RateLimitExceeded) as exc_info:
        raise RateLimitExceeded("Rate limit test error")

    assert str(exc_info.value) == "Rate limit test error"
