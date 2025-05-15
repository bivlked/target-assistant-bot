import os
from dataclasses import dataclass
from pathlib import Path

# from dotenv import load_dotenv # Removed from here, should be called in main entry point
import re
import logging

# Load environment variables from .env file if it exists # This comment also refers to the removed call
# load_dotenv() # Removed call

BASE_DIR = Path(__file__).resolve().parent


def _int_env(var_name: str, default: int) -> int:
    """Converts an environment variable to int, ignoring extraneous characters.
    Returns default if the number is not found.
    """
    raw = os.getenv(var_name)
    if raw is None:
        return default
    m = re.search(r"-?\d+", raw)
    try:
        return int(m.group()) if m else default
    except Exception:
        return default


@dataclass(frozen=True)
class TelegramConfig:
    """Configuration for the Telegram Bot token."""

    token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")


@dataclass(frozen=True)
class OpenAIConfig:
    """Configuration for the OpenAI API client."""

    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    # Number of retry attempts in case of LLM error
    max_retries: int = _int_env("OPENAI_MAX_RETRIES", 2)


@dataclass
class GoogleConfig:
    """Configuration for Google API access, specifically for service account credentials.

    If a relative path is specified in the GOOGLE_CREDENTIALS_PATH environment variable
    (or if it is not set), it will be converted to an absolute path within
    the project directory. This avoids issues when the bot is run from
    any directory or on a different OS (Windows vs Linux).
    """

    _raw_path: str = os.getenv("GOOGLE_CREDENTIALS_PATH", "google_credentials.json")

    @property
    def credentials_path(self) -> str:  # type: ignore[override]
        """Absolute path to the service account file.

        - If an absolute path is specified (e.g., `/opt/...`), it's returned as is.
        - Otherwise, the path is considered relative to `BASE_DIR`.

        Checks for file existence and provides guidance if not found.
        """

        path = Path(self._raw_path)
        if not path.is_absolute():
            path = BASE_DIR / path

        if not path.exists():
            # Try fallback path - file in the project root if not found via env var
            fallback = BASE_DIR / "google_credentials.json"
            if fallback.exists():
                logger = logging.getLogger(__name__)
                logger.warning(
                    "Google credentials file not found at '%s'. " "Using '%s' instead.",
                    path,
                    fallback,
                )
                path = fallback
            else:
                raise FileNotFoundError(
                    f"Google credentials file not found at '{path}' "
                    f"nor at fallback '{fallback}'. "
                    "Specify the correct path in GOOGLE_CREDENTIALS_PATH environment variable "
                    "or place 'google_credentials.json' in the project root."
                )

        return str(path)


@dataclass(frozen=True)
class SchedulerConfig:
    """Configuration for the task scheduler (APScheduler)."""

    timezone: str = os.getenv("SCHEDULER_TIMEZONE", "Europe/Moscow")
    morning_time: str = os.getenv("MORNING_REMINDER_TIME", "08:00")
    evening_time: str = os.getenv("EVENING_REMINDER_TIME", "20:00")
    motivation_interval_hours: int = _int_env("MOTIVATION_INTERVAL_HOURS", 8)


@dataclass(frozen=True)
class LoggingConfig:
    """Configuration for application logging."""

    level: str = os.getenv("LOG_LEVEL", "WARNING")
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass(frozen=True)
class RateLimiterConfig:
    """Configuration for API rate limiting, specifically for LLM calls."""

    # For LLM calls, e.g., OpenAI
    llm_requests_per_minute: int = _int_env(
        "LLM_REQUESTS_PER_MINUTE", 20
    )  # Default: 20 RPM per user
    llm_max_burst: int = _int_env(
        "LLM_MAX_BURST", 5
    )  # Default: allow burst of 5 requests


telegram = TelegramConfig()
openai_cfg = OpenAIConfig()
google = GoogleConfig()
scheduler_cfg = SchedulerConfig()
logging_cfg = LoggingConfig()
ratelimiter_cfg = RateLimiterConfig()
