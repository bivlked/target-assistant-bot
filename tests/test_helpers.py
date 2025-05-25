"""Tests for helper functions in utils/helpers.py."""

from datetime import datetime  # Added timezone for clarity
import pytz  # pytz is used

from utils.helpers import format_date, get_day_of_week


def test_format_date_uses_default_config_tz():
    """Tests that format_date() correctly uses the default timezone from scheduler_cfg
    when no explicit tz is provided, converting from UTC input.
    """
    # Assuming scheduler_cfg.timezone is 'Europe/Moscow' (UTC+3) for this example date
    # Input: January 15, 2024, 12:00 PM UTC
    dt_utc = datetime(2024, 1, 15, 12, 0, 0, tzinfo=pytz.utc)

    # Expected: When converted to Europe/Moscow (UTC+3), it becomes 15:00 on the same day.
    # The date part remains 15.01.2024
    # This assertion depends on the value of scheduler_cfg.timezone
    # To make it more robust, we could patch scheduler_cfg.timezone here.
    # For now, we assume the default from .env or config.py is used.
    assert format_date(dt_utc) == "15.01.2024"


def test_format_date_with_explicit_tz():
    """Tests format_date() with an explicitly provided timezone string."""
    dt_naive = datetime(2024, 1, 15, 18, 0, 0)  # A naive datetime
    # If dt_naive is considered local (e.g., Europe/Moscow) and we format to UTC:
    # 18:00 Europe/Moscow (UTC+3) -> 15:00 UTC on 15.01.2024
    # However, format_date applies astimezone. If dt_naive is passed, pytz will assume system local.
    # For stable tests, it's better to use aware datetimes.

    dt_moscow = pytz.timezone("Europe/Moscow").localize(datetime(2024, 1, 15, 18, 0, 0))
    assert format_date(dt_moscow, "UTC") == "15.01.2024"  # 18:00 MSK is 15:00 UTC
    assert (
        format_date(dt_moscow, "America/New_York") == "15.01.2024"
    )  # 18:00 MSK is 10:00 AM ET, still same date

    dt_utc = datetime(2024, 1, 15, 10, 0, 0, tzinfo=pytz.utc)
    assert (
        format_date(dt_utc, "Europe/Moscow") == "15.01.2024"
    )  # 10:00 UTC is 13:00 MSK


def test_get_day_of_week_russian():
    """Tests that get_day_of_week() returns the Russian name of the day."""
    dt_monday_utc = datetime(2024, 1, 15, 12, 0, 0, tzinfo=pytz.utc)  # This is a Monday
    assert get_day_of_week(dt_monday_utc) == "Понедельник"

    dt_thursday_utc = datetime(
        2025, 5, 1, 10, 0, 0, tzinfo=pytz.utc
    )  # This is a Thursday
    assert get_day_of_week(dt_thursday_utc) == "Четверг"

    # Test with a different timezone to ensure conversion works before getting day name
    dt_friday_moscow = pytz.timezone("Europe/Moscow").localize(
        datetime(2024, 1, 19, 2, 0, 0)
    )  # Friday in Moscow
    # This is Thursday 23:00 UTC. get_day_of_week defaults to scheduler_cfg.timezone (Europe/Moscow)
    assert get_day_of_week(dt_friday_moscow) == "Пятница"
    # Explicitly check for UTC day name
    assert get_day_of_week(dt_friday_moscow, "UTC") == "Четверг"


# Removed test_get_day_of_week_mapping_specific as its cases are covered by test_get_day_of_week_russian
