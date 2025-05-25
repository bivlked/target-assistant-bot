"""Tests for utils modules to improve coverage."""

import pytest
from datetime import datetime

# Test cache.py
from utils.cache import (
    sheet_cache_instance,
    invalidate_sheet_cache,
    cached_sheet_method,
    TTL_SECONDS,
)


def test_cache_operations():
    """Test basic cache operations."""
    user_id = 12345
    cache_key = (user_id, "test_method:key1")
    data = {"test": "data", "items": [1, 2, 3]}

    # Initially cache should be empty
    assert sheet_cache_instance._get_from_store(cache_key) is None

    # Set cache
    sheet_cache_instance._put_in_store(cache_key, data)

    # Get from cache
    cached = sheet_cache_instance._get_from_store(cache_key)
    assert cached == data

    # Invalidate cache
    invalidate_sheet_cache(user_id)
    assert sheet_cache_instance._get_from_store(cache_key) is None


def test_cache_ttl(monkeypatch):
    """Test cache TTL expiration."""
    import time

    user_id = 99999
    cache_key = (user_id, "test_method:ttl_test")
    data = {"ttl": "test"}

    # Set cache
    sheet_cache_instance._put_in_store(cache_key, data)
    assert sheet_cache_instance._get_from_store(cache_key) == data

    # Mock time to be after TTL
    original_time = time.time
    monkeypatch.setattr(time, "time", lambda: original_time() + TTL_SECONDS + 1)

    # Cache should be expired
    assert sheet_cache_instance._get_from_store(cache_key) is None


def test_cached_sheet_method_decorator():
    """Test the cached_sheet_method decorator."""
    call_count = 0

    class MockSheetManager:
        @cached_sheet_method(lambda target_date: target_date)
        def get_task_for_date(self, user_id: int, target_date: str):
            nonlocal call_count
            call_count += 1
            return {"task": f"Task for {target_date}"}

    manager = MockSheetManager()
    user_id = 55555

    # First call should execute the method
    result1 = manager.get_task_for_date(user_id, "25.05.2025")
    assert call_count == 1
    assert result1["task"] == "Task for 25.05.2025"

    # Second call should return cached result
    result2 = manager.get_task_for_date(user_id, "25.05.2025")
    assert call_count == 1  # No additional call
    assert result2 == result1

    # Different date should call the method again
    result3 = manager.get_task_for_date(user_id, "26.05.2025")
    assert call_count == 2
    assert result3["task"] == "Task for 26.05.2025"

    # Invalidate cache and try again
    invalidate_sheet_cache(user_id)
    result4 = manager.get_task_for_date(user_id, "25.05.2025")
    assert call_count == 3  # Method called again after invalidation


# Test helpers.py
from utils.helpers import format_date, get_day_of_week


def test_format_date():
    """Test date formatting."""
    # Test with specific date
    dt = datetime(2025, 5, 25, 10, 30, 45)
    assert format_date(dt) == "25.05.2025"

    # Test current date (just check format)
    today_str = format_date(datetime.now())
    assert len(today_str) == 10
    assert today_str[2] == "."
    assert today_str[5] == "."


def test_get_day_of_week():
    """Test day of week function."""
    # Test known dates
    dt1 = datetime(2025, 5, 25)  # Sunday
    assert get_day_of_week(dt1) == "Воскресенье"

    dt2 = datetime(2025, 5, 26)  # Monday
    assert get_day_of_week(dt2) == "Понедельник"

    dt3 = datetime(2025, 5, 27)  # Tuesday
    assert get_day_of_week(dt3) == "Вторник"


# Test ratelimiter.py
from utils.ratelimiter import UserRateLimiter, RateLimitException


def test_rate_limiter_basic():
    """Test basic rate limiter functionality."""
    limiter = UserRateLimiter(default_tokens_per_second=1.0, default_max_tokens=5.0)

    user_id = 111

    # Should work for first few requests
    for _ in range(3):
        limiter.check_limit(user_id)  # Should not raise

    # Should raise after exhausting tokens
    with pytest.raises(RateLimitException) as exc_info:
        for _ in range(10):  # Try many times to ensure we hit the limit
            limiter.check_limit(user_id)

    assert "Rate limit exceeded" in str(exc_info.value)


def test_rate_limiter_custom_cost():
    """Test rate limiter with custom tokens to consume."""
    limiter = UserRateLimiter(default_tokens_per_second=1.0, default_max_tokens=10.0)

    user_id = 222

    # Use high tokens_to_consume
    limiter.check_limit(user_id, tokens_to_consume=5)  # Should work
    limiter.check_limit(user_id, tokens_to_consume=4)  # Should work

    # Next request should fail
    with pytest.raises(RateLimitException):
        limiter.check_limit(user_id, tokens_to_consume=5)


# Test retry_decorators.py
from utils.retry_decorators import retry_openai_llm


@pytest.mark.asyncio
async def test_retry_decorator_success():
    """Test retry decorator with successful function."""
    call_count = 0

    @retry_openai_llm
    async def successful_func():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await successful_func()
    assert result == "success"
    assert call_count == 1


def test_retry_decorator_basic():
    """Test basic retry decorator functionality."""
    from utils.retry_decorators import _log_retry
    from tenacity import RetryCallState
    from unittest.mock import Mock

    # Test _log_retry function
    retry_state = Mock(spec=RetryCallState)
    retry_state.outcome = Mock()
    retry_state.outcome.failed = True
    retry_state.outcome.exception.return_value = Exception("Test error")
    retry_state.fn = Mock(__name__="test_function")
    retry_state.attempt_number = 2
    retry_state.retry_object = Mock()
    retry_state.retry_object.stop = Mock(max_attempt_number=3)

    # Should not raise
    _log_retry(retry_state)


# Test sentry_integration.py
from utils.sentry_integration import setup_sentry


def test_sentry_setup_without_dsn(monkeypatch):
    """Test Sentry setup when DSN is not configured."""
    monkeypatch.setenv("SENTRY_DSN", "")

    # Should not raise, just skip initialization
    setup_sentry()


def test_sentry_setup_with_dsn(monkeypatch):
    """Test Sentry setup with DSN configured."""
    monkeypatch.setenv("SENTRY_DSN", "https://test@sentry.io/123456")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "test")

    # Should initialize without errors
    setup_sentry()
