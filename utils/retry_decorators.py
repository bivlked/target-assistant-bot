"""Standardized Tenacity retry decorators for external API calls.

This module provides pre-configured `tenacity.retry` decorators for common
API interaction patterns within the application, such as calls to Google Sheets
and OpenAI LLM. It includes a shared logging callback (`_log_retry`) to
report retry attempts.

Key decorators:
- `retry_google_sheets`: For gspread API calls.
- `retry_openai_llm`: For OpenAI API calls, reraises exceptions.
- `retry_openai_llm_no_reraise`: For OpenAI calls where returning None on failure is preferred.
"""

from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
    RetryCallState,
)
from openai import APIError as OpenAI_APIError
from gspread.exceptions import APIError as GSpread_APIError  # type: ignore
import logging

from config import openai_cfg  # For max_retries

logger = logging.getLogger(__name__)


def _log_retry(retry_state: RetryCallState):
    """Callback function for Tenacity to log retry attempts.

    Args:
        retry_state: The current state of the retry call, provided by Tenacity.
                     Includes information like attempt number, outcome, and the
                     function being retried.
    """
    if retry_state.outcome and retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        stop_condition = retry_state.retry_object.stop
        max_attempts_str = "many"
        if isinstance(stop_condition, stop_after_attempt):
            max_attempts_str = str(stop_condition.max_attempt_number)

        logger.warning(
            f"Retrying {retry_state.fn.__name__ if retry_state.fn else 'function'} "
            f"due to {type(exception).__name__}: {exception}. "
            f"Attempt {retry_state.attempt_number} of {max_attempts_str}."
        )


# Retry decorator for Google Sheets API calls
retry_google_sheets = retry(
    retry=retry_if_exception_type(GSpread_APIError),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    before_sleep=_log_retry,
    reraise=True,
)

# Retry decorator for OpenAI API calls
retry_openai_llm = retry(
    retry=retry_if_exception_type(OpenAI_APIError),
    wait=wait_exponential(
        multiplier=1, min=2, max=15
    ),  # Slightly longer initial wait and max
    stop=stop_after_attempt(
        openai_cfg.max_retries if openai_cfg.max_retries > 0 else 3
    ),  # Ensure positive attempts
    before_sleep=_log_retry,
    reraise=True,
)

# Specific retry for period_parser LLM call that should not reraise but return None
retry_openai_llm_no_reraise = retry(
    retry=retry_if_exception_type(OpenAI_APIError),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    stop=stop_after_attempt(2),
    before_sleep=_log_retry,
    reraise=False,  # Important: returns the result of the last attempt or None if all fail
)
