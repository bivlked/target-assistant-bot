import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
import re

# Загружаем переменные окружения из .env файла, если он существует
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _int_env(var_name: str, default: int) -> int:
    """Преобразует переменную окружения в int, игнорируя посторонние символы.
    Если число не найдено, возвращает default.
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
    token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    # Количество попыток повторного запроса в случае ошибки LLM
    max_retries: int = int(os.getenv("OPENAI_MAX_RETRIES", "2"))


@dataclass(frozen=True)
class GoogleConfig:
    credentials_path: str = os.getenv("GOOGLE_CREDENTIALS_PATH", "google_credentials.json")


@dataclass(frozen=True)
class SchedulerConfig:
    timezone: str = os.getenv("SCHEDULER_TIMEZONE", "Europe/Moscow")
    morning_time: str = os.getenv("MORNING_REMINDER_TIME", "08:00")
    evening_time: str = os.getenv("EVENING_REMINDER_TIME", "20:00")
    motivation_interval_hours: int = _int_env("MOTIVATION_INTERVAL_HOURS", 8)


@dataclass(frozen=True)
class LoggingConfig:
    level: str = os.getenv("LOG_LEVEL", "WARNING")
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


telegram = TelegramConfig()
openai_cfg = OpenAIConfig()
google = GoogleConfig()
scheduler_cfg = SchedulerConfig()
logging_cfg = LoggingConfig() 