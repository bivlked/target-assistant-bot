"""Tests for retry decorators in utils/retry_decorators.py."""

import pytest
import logging
from unittest.mock import MagicMock, patch

from tenacity import RetryCallState, Future, AttemptManager
from openai import APIError as OpenAI_APIError  # Нужен для тестов декораторов
from gspread.exceptions import (
    APIError as GSpread_APIError,
)  # Нужен для тестов декораторов

from utils.retry_decorators import (
    _log_retry,
    retry_google_sheets,
    retry_openai_llm,
    retry_openai_llm_no_reraise,
)

# --- Test for _log_retry ---


def test_log_retry_when_failed():
    """Tests that _log_retry logs a warning when the outcome has failed."""
    mock_retry_state = MagicMock(spec=RetryCallState)
    mock_retry_state.outcome = MagicMock(spec=Future)
    mock_retry_state.outcome.failed = True
    mock_exception = ValueError("Test exception")
    mock_retry_state.outcome.exception.return_value = mock_exception
    mock_retry_state.attempt_number = 3

    # Mocking retry_state.fn (function being retried)
    mock_function = MagicMock()
    mock_function.__name__ = "test_function_being_retried"
    mock_retry_state.fn = mock_function

    # Mocking retry_state.retry_object.stop for stop_after_attempt
    mock_stop_condition = MagicMock(spec=AttemptManager)
    mock_stop_condition.max_attempt_number = 5
    mock_retry_state.retry_object.stop = mock_stop_condition

    with patch("utils.retry_decorators.logger.warning") as mock_logger_warning:
        _log_retry(mock_retry_state)
        mock_logger_warning.assert_called_once()
        call_args_str = str(mock_logger_warning.call_args)
        assert "Retrying test_function_being_retried" in call_args_str
        assert "due to ValueError: Test exception" in call_args_str
        assert "Attempt 3 of 5" in call_args_str


def test_log_retry_when_not_failed():
    """Tests that _log_retry does not log if outcome is not failed."""
    mock_retry_state = MagicMock(spec=RetryCallState)
    mock_retry_state.outcome = MagicMock(spec=Future)
    mock_retry_state.outcome.failed = False  # Outcome did not fail

    with patch("utils.retry_decorators.logger.warning") as mock_logger_warning:
        _log_retry(mock_retry_state)
        mock_logger_warning.assert_not_called()


def test_log_retry_no_outcome():
    """Tests that _log_retry does not log if there is no outcome."""
    mock_retry_state = MagicMock(spec=RetryCallState)
    mock_retry_state.outcome = None  # No outcome

    with patch("utils.retry_decorators.logger.warning") as mock_logger_warning:
        _log_retry(mock_retry_state)
        mock_logger_warning.assert_not_called()


# --- Tests for decorators ---


# Helper function to be decorated
def mock_successful_api_call(*args, **kwargs):
    """Simulates a successful API call."""
    return "success"


# Counter for mock_failing_api_call attempts
fail_call_count = 0


def mock_failing_api_call_then_succeed(max_fails, *args, **kwargs):
    """Simulates an API call that fails a few times then succeeds."""
    global fail_call_count
    fail_call_count += 1
    if fail_call_count <= max_fails:
        # print(f"DEBUG: mock_failing_api_call_then_succeed attempt {fail_call_count} -> failing with OpenAI_APIError")
        raise OpenAI_APIError("Simulated API failure", request=MagicMock(), body=None)
    # print(f"DEBUG: mock_failing_api_call_then_succeed attempt {fail_call_count} -> succeeding")
    return "success after retries"


def mock_always_failing_api_call(*args, **kwargs):
    """Simulates an API call that always fails."""
    # print(f"DEBUG: mock_always_failing_api_call called, raising OpenAI_APIError")
    raise OpenAI_APIError(
        "Simulated persistent API failure", request=MagicMock(), body=None
    )


@pytest.fixture(autouse=True)
def reset_fail_call_counter():
    """Resets the global fail_call_count before each test that might use it."""
    global fail_call_count
    fail_call_count = 0


# --- Tests for retry_openai_llm ---


def test_retry_openai_llm_success_first_try():
    """Tests @retry_openai_llm when the decorated function succeeds on the first try."""
    decorated_func = retry_openai_llm(mock_successful_api_call)
    with patch("utils.retry_decorators._log_retry") as mock_log_retry_fn:
        result = decorated_func()
        assert result == "success"
        mock_log_retry_fn.assert_not_called()


@pytest.mark.asyncio  # Декоратор retry_openai_llm может применяться и к async функциям
async def test_retry_openai_llm_async_success_first_try():
    """Tests @retry_openai_llm with an async function succeeding on the first try."""

    async def async_mock_successful_api_call(*args, **kwargs):
        return "async success"

    decorated_func = retry_openai_llm(async_mock_successful_api_call)
    with patch("utils.retry_decorators._log_retry") as mock_log_retry_fn:
        result = await decorated_func()
        assert result == "async success"
        mock_log_retry_fn.assert_not_called()


def test_retry_openai_llm_retries_and_succeeds(reset_fail_call_counter):
    """Tests @retry_openai_llm when function fails then succeeds."""
    # retry_openai_llm по умолчанию имеет stop_after_attempt(config.openai_cfg.max_retries=2 или 3)
    # Пусть он упадет 1 раз, а на 2-й пройдет
    max_fails_for_test = 1

    # Применяем декоратор к функции, которая будет падать
    decorated_func = retry_openai_llm(
        lambda: mock_failing_api_call_then_succeed(max_fails_for_test)
    )

    with patch("utils.retry_decorators._log_retry") as mock_log_retry_fn:
        result = decorated_func()
        assert result == "success after retries"
        assert fail_call_count == max_fails_for_test + 1
        assert mock_log_retry_fn.call_count == max_fails_for_test


def test_retry_openai_llm_fails_all_attempts_and_reraises(reset_fail_call_counter):
    """Tests @retry_openai_llm when function always fails; should reraise."""
    decorated_func = retry_openai_llm(mock_always_failing_api_call)

    # Импортируем config здесь, чтобы получить актуальное значение max_retries
    # Это важно, если другие тесты могут изменять конфигурацию через monkeypatch
    # или если модуль config был перезагружен.
    import config

    expected_log_calls = max(0, config.openai_cfg.max_retries - 1)

    with patch("utils.retry_decorators.logger.warning") as mock_logger_warning:
        with pytest.raises(OpenAI_APIError) as excinfo:  # Используем вложенный with
            decorated_func()

    assert "Simulated persistent API failure" in str(excinfo.value)
    assert mock_logger_warning.call_count == expected_log_calls


# TODO: Аналогичные тесты для retry_google_sheets и retry_openai_llm_no_reraise

# --- Placeholder for decorator tests (to be implemented next) ---
# TODO: Add tests for retry_google_sheets
# TODO: Add tests for retry_openai_llm
# TODO: Add tests for retry_openai_llm_no_reraise
