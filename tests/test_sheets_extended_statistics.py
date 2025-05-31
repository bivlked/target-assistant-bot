"""Tests for the get_extended_statistics method of SheetsManager and AsyncSheetsManager."""

import pytest
import pytest_asyncio  # Добавляем импорт
from typing import List, Dict, Tuple
from freezegun import freeze_time  # Import freezegun
from unittest.mock import MagicMock, patch  # For mocking managers if needed

from sheets.client import (
    SheetsManager,
)  # Убедимся, что PLAN_SAMPLE здесь НЕ импортируется
from sheets.async_client import AsyncSheetsManager  # Import AsyncSheetsManager
from core.models import Goal, GoalStatus, GoalPriority

# Константы для ключей, если они нужны, должны импортироваться отдельно или быть определены
# from sheets.client import COL_DATE, COL_STATUS, etc. - если они нужны глобально в этом файле

# --- Helpers ---------------------------------------------------------------

# Оставляем PLAN_SAMPLE определенным здесь локально
PLAN_SAMPLE: List[Dict[str, str]] = [
    {
        "Дата": "01.05.2025",  # Используем строки, как они есть в sheets.client
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
def freeze_today_for_stats():
    """Freezes time to a specific date for consistent testing of date-dependent statistics."""
    with freeze_time("2025-05-02"):  # Date chosen to interact with PLAN_SAMPLE
        yield


@pytest.fixture
def mock_sheets_manager_for_stats(monkeypatch: pytest.MonkeyPatch) -> SheetsManager:
    """Provides a SheetsManager instance with _get_spreadsheet and worksheet.get_all_records mocked."""
    manager = SheetsManager()  # Relies on conftest.patch_gspread for gc

    mock_spreadsheet = MagicMock(name="SpreadsheetMock")
    mock_plan_worksheet = MagicMock(name="PlanWorksheetMock")
    mock_plan_worksheet.get_all_records.return_value = PLAN_SAMPLE

    # _get_spreadsheet возвращает мок спреда
    monkeypatch.setattr(manager, "_get_spreadsheet", lambda user_id: mock_spreadsheet)
    # worksheet(PLAN_SHEET) на этом спреде возвращает мок листа плана
    mock_spreadsheet.worksheet.return_value = mock_plan_worksheet
    # Дополнительно мокаем URL, так как он используется в get_extended_statistics
    mock_spreadsheet.url = "http://fake.com/sheet_url"
    return manager


@pytest_asyncio.fixture  # Используем правильный декоратор
async def mock_async_sheets_manager_for_stats(
    monkeypatch: pytest.MonkeyPatch,
) -> Tuple[AsyncSheetsManager, MagicMock]:
    """Provides an AsyncSheetsManager with underlying sync manager methods mocked for stats."""
    async_manager = AsyncSheetsManager()

    # Мокаем синхронный экземпляр _sync, который использует AsyncSheetsManager
    sync_manager_mock = MagicMock(spec=SheetsManager)

    # Мокаем методы синхронного менеджера, которые будут вызваны
    # _get_spreadsheet будет вызван внутри get_extended_statistics синхронного менеджера
    mock_spreadsheet = MagicMock(name="SpreadsheetMockForAsync")
    mock_plan_worksheet = MagicMock(name="PlanWorksheetMockForAsync")
    mock_plan_worksheet.get_all_records.return_value = PLAN_SAMPLE
    mock_spreadsheet.worksheet.return_value = mock_plan_worksheet
    mock_spreadsheet.url = "http://fake.com/async_sheet_url"

    # Мокаем _get_spreadsheet у sync_manager_mock
    # Это немного сложнее, так как get_extended_statistics вызывает его косвенно.
    # Проще всего мокнуть сам get_extended_statistics у sync_manager_mock.
    expected_stats_result = (
        {  # Результат, который вернул бы синхронный get_extended_statistics
            "total_days": 3,
            "completed_days": 1,
            "progress_percent": 33,
            "days_passed": 1,
            "days_left": 2,
            "upcoming_tasks": [PLAN_SAMPLE[1], PLAN_SAMPLE[2]],  # T2, T3
            "sheet_url": "http://fake.com/async_sheet_url",
        }
    )
    sync_manager_mock.get_extended_statistics = MagicMock(
        return_value=expected_stats_result
    )

    monkeypatch.setattr(async_manager, "_sync", sync_manager_mock)
    return async_manager, sync_manager_mock  # Возвращаем и async, и мок синхронного


# --------------------------------------------------------------------------
#                               Sync version
# --------------------------------------------------------------------------


def test_get_extended_statistics_sync(mock_sheets_manager_for_stats: SheetsManager):
    """Tests synchronous get_extended_statistics with mocked data."""
    # freeze_today_for_stats (02.05.2025) должен быть активен
    manager = mock_sheets_manager_for_stats

    # Мокаем get_active_goals чтобы вернуть одну активную цель
    mock_goal = Goal(
        goal_id=1,
        name="Test Goal",
        description="Test Description",
        deadline="30 дней",
        daily_time="1 час",
        start_date="01.05.2025",
        status=GoalStatus.ACTIVE,
        priority=GoalPriority.MEDIUM,
        tags=[],
        progress_percent=33,
    )

    # Создаем моки для методов
    mock_get_active_goals = MagicMock(return_value=[mock_goal])
    mock_get_goal_statistics = MagicMock(
        return_value=MagicMock(
            total_tasks=3,
            completed_tasks=1,
            progress_percent=33,
            days_elapsed=1,
            days_remaining=2,
            completion_rate=1.0,
        )
    )
    mock_get_plan_for_goal = MagicMock(
        return_value=[
            MagicMock(
                date="01.05.2025",
                day_of_week="Четверг",
                task="T1",
                status=MagicMock(value="Выполнено"),
            ),
            MagicMock(
                date="02.05.2025",
                day_of_week="Пятница",
                task="T2",
                status=MagicMock(value="Не выполнено"),
            ),
            MagicMock(
                date="03.05.2025",
                day_of_week="Суббота",
                task="T3",
                status=MagicMock(value="Не выполнено"),
            ),
        ]
    )

    # Используем unittest.mock.patch.object для патчинга методов

    with (
        patch.object(manager, "get_active_goals", mock_get_active_goals),
        patch.object(manager, "get_goal_statistics", mock_get_goal_statistics),
        patch.object(manager, "get_plan_for_goal", mock_get_plan_for_goal),
    ):

        stats = manager.get_extended_statistics(user_id=11)

    assert stats["total_days"] == 3
    assert stats["completed_days"] == 1
    assert stats["progress_percent"] == 33  # 1/3 = 33%
    assert stats["days_passed"] == 1  # 01.05 прошел относительно 02.05
    assert stats["days_left"] == 2  # 3 - 1 = 2
    assert len(stats["upcoming_tasks"]) == 2
    assert stats["upcoming_tasks"][0]["Задача"] == "T2"  # 02.05 - сегодня
    assert stats["upcoming_tasks"][1]["Задача"] == "T3"  # 03.05 - будущее
    assert stats["sheet_url"] == "http://fake.com/sheet_url"


# --------------------------------------------------------------------------
#                               Async wrapper
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_extended_statistics_async(
    mock_async_sheets_manager_for_stats: Tuple[AsyncSheetsManager, MagicMock],
):
    """Tests asynchronous get_extended_statistics."""
    async_manager, sync_mock = mock_async_sheets_manager_for_stats

    user_id_to_test = 12
    # upcoming_count не передаем, чтобы использовалось значение по умолчанию (5)
    stats = await async_manager.get_extended_statistics(user_id=user_id_to_test)

    # Проверяем, что AsyncSheetsManager правильно вызвал метод своего мокнутого _sync экземпляра
    # с user_id позиционно и upcoming_count=5 (дефолтное значение)
    sync_mock.get_extended_statistics.assert_called_once_with(user_id_to_test, 5)

    # Ассерты на результат, который вернул мок sync_mock.get_extended_statistics
    assert stats["total_days"] == 3
    assert stats["completed_days"] == 1
    assert stats["progress_percent"] == 33
    assert stats["days_passed"] == 1
    assert stats["days_left"] == 2
    assert len(stats["upcoming_tasks"]) == 2
    assert stats["upcoming_tasks"][0]["Задача"] == "T2"
    assert stats["sheet_url"] == "http://fake.com/async_sheet_url"

    await async_manager.aclose()
