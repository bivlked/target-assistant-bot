from datetime import datetime
import pytz

from config import scheduler_cfg


def format_date(date_obj: datetime, tz: str | None = None) -> str:
    tzinfo = pytz.timezone(tz or scheduler_cfg.timezone)
    return date_obj.astimezone(tzinfo).strftime("%d.%m.%Y")


def get_day_of_week(date_obj: datetime, tz: str | None = None) -> str:
    tzinfo = pytz.timezone(tz or scheduler_cfg.timezone)
    day = date_obj.astimezone(tzinfo).strftime("%A")
    mapping = {
        "Monday": "Понедельник",
        "Tuesday": "Вторник",
        "Wednesday": "Среда",
        "Thursday": "Четверг",
        "Friday": "Пятница",
        "Saturday": "Суббота",
        "Sunday": "Воскресенье",
    }
    return mapping.get(day, day)
