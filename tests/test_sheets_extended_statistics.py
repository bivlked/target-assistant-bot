import pytest

from typing import List, Dict

# --- Helpers ---------------------------------------------------------------

PLAN_SAMPLE: List[Dict[str, str]] = [
    {
        "Дата": "01.05.2025",
        "День недели": "Четверг",
        "Задача": "T1",
        "Статус": "Выполнено",
    },
    {
        "Дата": "02.05.2025",
        "День недели": "Пятница",
        "Задача": "T2",
        "Статус": "Не выполнено",
    },
    {
        "Дата": "03.05.2025",
        "День недели": "Суббота",
        "Задача": "T3",
        "Статус": "Не выполнено",
    },
]


@pytest.fixture(autouse=True)
def _freeze_today(monkeypatch):
    """Фиксируем utils.helpers.format_date, чтобы SheetsManager считал сегодня 02.05.2025."""

    monkeypatch.setattr(
        "utils.helpers.format_date", lambda dt, tz=None: "02.05.2025", raising=False
    )


# --------------------------------------------------------------------------
#                               Sync version
# --------------------------------------------------------------------------


def test_get_extended_statistics_sync():
    from sheets.client import SheetsManager

    mgr = SheetsManager()
    mgr.save_plan(11, PLAN_SAMPLE)

    stats = mgr.get_extended_statistics(11)

    assert stats["total_days"] == 3
    assert stats["completed_days"] == 1
    assert stats["progress_percent"] == 33
    assert stats["days_passed"] == 1  # только 01.05 прошло
    assert stats["days_left"] == 2
    assert len(stats["upcoming_tasks"]) == 2
    assert stats["upcoming_tasks"][0]["Дата"] == "02.05.2025"


# --------------------------------------------------------------------------
#                               Async wrapper
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_extended_statistics_async():
    from sheets.async_client import AsyncSheetsManager

    mgr = AsyncSheetsManager(max_workers=2)
    await mgr.save_plan(12, PLAN_SAMPLE)

    stats = await mgr.get_extended_statistics(12)

    assert stats["total_days"] == 3
    assert stats["completed_days"] == 1
    assert stats["progress_percent"] == 33

    # проверяем, что проксирование async -> sync работает
    assert len(stats["upcoming_tasks"]) == 2

    await mgr.aclose()  # корректное закрытие executor
