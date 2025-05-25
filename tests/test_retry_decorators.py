"""Tests for retry decorators in utils/retry_decorators.py."""

import pytest
from unittest.mock import MagicMock, patch

from tenacity import (
    RetryCallState,
    Future,
    stop_after_attempt,
    RetryError,
)
from openai import APIError as OpenAI_APIError  # Нужен для тестов декораторов
from gspread.exceptions import (
    APIError as GSpread_APIError,
)  # Нужен для тестов декораторов
import requests  # Новый импорт

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

    mock_function = MagicMock()
    mock_function.__name__ = "test_function_being_retried"
    mock_retry_state.fn = mock_function

    # Create a mock for the retry_object and its stop condition
    mock_retry_object = MagicMock()
    mock_stop_condition = stop_after_attempt(5)
    mock_retry_object.stop = mock_stop_condition
    mock_retry_state.retry_object = mock_retry_object  # Assign mock_retry_object

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
    max_fails_for_test = 1

    decorated_func = retry_openai_llm(
        lambda: mock_failing_api_call_then_succeed(max_fails_for_test)
    )

    # Патчим logger.warning, который вызывается внутри _log_retry
    with patch("utils.retry_decorators.logger.warning") as mock_logger_warning_actual:
        result = decorated_func()
        assert result == "success after retries"
        assert fail_call_count == max_fails_for_test + 1
        assert mock_logger_warning_actual.call_count == max_fails_for_test


def test_retry_openai_llm_fails_all_attempts_and_reraises(reset_fail_call_counter):
    """Tests @retry_openai_llm when function always fails; should reraise."""
    decorated_func = retry_openai_llm(mock_always_failing_api_call)

    import config

    expected_log_calls = max(0, config.openai_cfg.max_retries - 1)

    # Патчим logger.warning
    with patch("utils.retry_decorators.logger.warning") as mock_logger_warning_actual:
        with pytest.raises(OpenAI_APIError) as excinfo:  # Вложенный with
            decorated_func()

    assert "Simulated persistent API failure" in str(excinfo.value)
    assert mock_logger_warning_actual.call_count == expected_log_calls


# --- Tests for retry_google_sheets ---


def mock_failing_gspread_call_then_succeed(max_fails, *args, **kwargs):
    """Simulates a gspread API call that fails a few times then succeeds."""
    global fail_call_count
    fail_call_count += 1
    if fail_call_count <= max_fails:
        mock_response = MagicMock(
            spec=requests.Response
        )  # Используем requests.Response
        mock_response.text = "Simulated GSpread API failure content"
        mock_response.status_code = 500
        raise GSpread_APIError(mock_response)
    return "gspread success after retries"


def mock_always_failing_gspread_call(*args, **kwargs):
    """Simulates a gspread API call that always fails."""
    mock_response = MagicMock(spec=requests.Response)  # Используем requests.Response
    mock_response.text = "Simulated persistent GSpread API failure content"
    mock_response.status_code = 500
    raise GSpread_APIError(mock_response)


def test_retry_google_sheets_success_first_try():
    """Tests @retry_google_sheets when the decorated function succeeds on the first try."""
    decorated_func = retry_google_sheets(
        mock_successful_api_call
    )  # Используем тот же mock_successful_api_call
    with patch("utils.retry_decorators._log_retry") as mock_log_retry_fn:
        result = decorated_func()
        assert result == "success"
        mock_log_retry_fn.assert_not_called()


def test_retry_google_sheets_retries_and_succeeds(reset_fail_call_counter):
    """Tests @retry_google_sheets when function fails then succeeds."""
    max_fails_for_test = 2
    decorated_func = retry_google_sheets(
        lambda: mock_failing_gspread_call_then_succeed(max_fails_for_test)
    )

    with patch(
        "utils.retry_decorators.logger.warning"
    ) as mock_logger_warning:  # Патчим logger.warning
        result = decorated_func()
        assert result == "gspread success after retries"
        assert fail_call_count == max_fails_for_test + 1
        assert mock_logger_warning.call_count == max_fails_for_test


def test_retry_google_sheets_fails_all_attempts_and_reraises(reset_fail_call_counter):
    """Tests @retry_google_sheets when function always fails; should reraise."""
    decorated_func = retry_google_sheets(mock_always_failing_gspread_call)
    expected_log_calls = 3 - 1

    with patch(
        "utils.retry_decorators.logger.warning"
    ) as mock_logger_warning:  # Патчим logger.warning
        with pytest.raises(GSpread_APIError) as excinfo:
            decorated_func()

    assert "Simulated persistent GSpread API failure content" in str(
        excinfo.value
    )  # Проверяем текст из мока Response
    assert mock_logger_warning.call_count == expected_log_calls


# --- Tests for retry_openai_llm_no_reraise ---


def test_retry_openai_llm_no_reraise_success_first_try():
    """Tests @retry_openai_llm_no_reraise with success on first try."""
    decorated_func = retry_openai_llm_no_reraise(mock_successful_api_call)
    with patch("utils.retry_decorators.logger.warning") as mock_logger_warning:
        result = decorated_func()
        assert result == "success"
        mock_logger_warning.assert_not_called()


def test_retry_openai_llm_no_reraise_retries_and_succeeds(reset_fail_call_counter):
    """Tests @retry_openai_llm_no_reraise when function fails then succeeds."""
    # stop_after_attempt(2). Fails 1 time, succeeds on 2nd.
    max_fails_for_test = 1
    decorated_func = retry_openai_llm_no_reraise(
        lambda: mock_failing_api_call_then_succeed(max_fails_for_test)
    )
    with patch("utils.retry_decorators.logger.warning") as mock_logger_warning:
        result = decorated_func()
        assert result == "success after retries"
        assert fail_call_count == max_fails_for_test + 1
        assert mock_logger_warning.call_count == max_fails_for_test  # Logged 1 time


def test_retry_openai_llm_no_reraise_fails_all_attempts_returns_none(
    reset_fail_call_counter,
):
    """Tests @retry_openai_llm_no_reraise when function always fails.
    It should not reraise the original error but tenacity will raise RetryError.
    """
    failing_func_mock = MagicMock(
        side_effect=OpenAI_APIError(
            "Persistent NoReraise Error", request=MagicMock(), body=None
        ),
        __name__="mocked_failing_function_for_no_reraise",
    )
    decorated_func = retry_openai_llm_no_reraise(failing_func_mock)
    expected_log_calls = 2 - 1

    with patch("utils.retry_decorators.logger.warning") as mock_logger_warning:
        with pytest.raises(RetryError) as excinfo_retry:  # Вложенный with
            decorated_func()

    assert isinstance(excinfo_retry.value.last_attempt.exception(), OpenAI_APIError)
    assert "Persistent NoReraise Error" in str(
        excinfo_retry.value.last_attempt.exception()
    )

    assert mock_logger_warning.call_count == expected_log_calls
    assert failing_func_mock.call_count == 2


# --- Placeholder for decorator tests (to be implemented next) ---
# TODO: Add tests for retry_google_sheets
# TODO: Add tests for retry_openai_llm
# TODO: Add tests for retry_openai_llm_no_reraise
