from datetime import datetime

import pytz

from utils.helpers import format_date, get_day_of_week


def test_format_date_default_tz():
    """format_date() должна вернуть dd.mm.yyyy в конф. тайм-зоне."""
    dt = datetime(2024, 1, 15, 12, 0, tzinfo=pytz.utc)
    assert format_date(dt) == "15.01.2024"


def test_get_day_of_week_ru():
    """get_day_of_week() возвращает русское название дня недели."""
    dt = datetime(2024, 1, 15, tzinfo=pytz.utc)  # Понедельник
    assert get_day_of_week(dt) == "Понедельник"


def test_get_day_of_week_mapping_specific():
    # 1 мая 2025 — четверг
    dt = datetime(2025, 5, 1, 10, 0, tzinfo=pytz.utc)
    assert get_day_of_week(dt) == "Четверг"
