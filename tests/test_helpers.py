from datetime import datetime

from utils.helpers import format_date, get_day_of_week


def test_format_date_default_tz():
    """format_date() возвращает дату в формате dd.mm.yyyy с таймзоной по умолчанию."""
    dt = datetime(2024, 1, 15, 12, 0, 0)
    assert format_date(dt) == "15.01.2024"


def test_get_day_of_week_ru():
    """get_day_of_week() возвращает название дня недели на русском."""
    dt = datetime(2024, 1, 15)  # Понедельник
    assert get_day_of_week(dt) == "Понедельник"
