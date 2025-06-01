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


def escape_markdown_v2(text: str) -> str:
    """Escapes special characters for MarkdownV2.

    See: https://core.telegram.org/bots/api#markdownv2-style
    """
    if not text:
        return ""
    # Order matters: escape backslashes first, then other special chars.
    # Special characters for MarkdownV2 from Telegram Bot API documentation.
    # Chars: _ * [ ] ( ) ~ ` > # + - = | { } . !
    # The `escape_chars` string contains all characters that need to be escaped.
    # It's crucial to escape the backslash itself first if it's used as a literal.
    # Then, iterate through other special characters.

    # Step 1: Escape backslashes. Replace each literal backslash with two backslashes.
    text = text.replace("\\", "\\\\")

    # Step 2: Define other special characters that need escaping.
    # Note: Backslash is handled above and not included here to avoid double escaping it.
    escape_chars = "_*[]()~`>#+-=|{}"

    # Step 3: Escape each special character.
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text
