"""General helper functions used across the application."""

from datetime import datetime
import pytz

from config import scheduler_cfg


def format_date(date_obj: datetime, tz: str | None = None) -> str:
    """Formats a datetime object to DD.MM.YYYY string in the specified timezone."""
    tzinfo = pytz.timezone(tz or scheduler_cfg.timezone)
    return date_obj.astimezone(tzinfo).strftime("%d.%m.%Y")


def get_day_of_week(date_obj: datetime, tz: str | None = None) -> str:
    """Gets the localized (Russian) name of the day of the week for a datetime object."""
    tzinfo = pytz.timezone(tz or scheduler_cfg.timezone)
    day = date_obj.astimezone(tzinfo).strftime("%A")
    # Mapping from English day names (from strftime) to Russian
    mapping = {
        "Monday": "Понедельник",
        "Tuesday": "Вторник",
        "Wednesday": "Среда",
        "Thursday": "Четверг",
        "Friday": "Пятница",
        "Saturday": "Суббота",
        "Sunday": "Воскресенье",
    }
    return mapping.get(
        day, day
    )  # Fallback to English name if not in map (should not happen for %A)
