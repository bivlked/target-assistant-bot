import pytest

from core.goal_manager import GoalManager
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS
from core.interfaces import AsyncStorageInterface, AsyncLLMInterface
from typing import cast, Any, Dict, List


class DummyAsyncSheets(AsyncStorageInterface):
    """Асинхронная заглушка SheetsManager."""

    def __init__(self):
        self.calls = {}

    async def clear_user_data(self, user_id: int):  # noqa: D401
        self.calls["clear_user_data"] = user_id

    async def save_goal_info(self, user_id: int, goal_info: dict):  # noqa: D401
        self.calls["save_goal_info"] = (user_id, goal_info)
        return "http://dummy_spreadsheet"

    async def save_plan(self, user_id: int, plan_rows: list):  # noqa: D401
        self.calls["save_plan"] = (user_id, plan_rows)

    # Add other StorageInterface methods as async stubs for interface compliance
    async def create_spreadsheet(self, user_id: int) -> None:
        pass

    async def delete_spreadsheet(self, user_id: int) -> None:
        pass

    async def get_task_for_date(self, user_id: int, date: str):
        # Simulate returning a task for specific test cases if needed, else None
        if hasattr(self, "_mock_task_for_date") and self._mock_task_for_date.get(date):
            return self._mock_task_for_date[date]
        return None

    async def update_task_status(self, user_id: int, date: str, status: str) -> None:
        pass

    async def batch_update_task_statuses(
        self, user_id: int, updates: Dict[str, str]
    ) -> None:
        pass

    async def get_statistics(self, user_id: int):
        return ""

    async def get_extended_statistics(self, user_id: int) -> Dict[str, Any]:
        # Simulate returning extended stats for specific test cases if needed
        if hasattr(self, "_mock_extended_stats"):
            return self._mock_extended_stats
        return {
            "total_days": 0,
            "completed_days": 0,
            "progress_percent": 0,
            "days_passed": 0,
            "days_left": 0,
            "upcoming_tasks": [],
            "sheet_url": "",
        }

    async def get_goal_info(self, user_id: int) -> Dict[str, Any]:
        if hasattr(self, "_mock_goal_info"):
            return self._mock_goal_info
        return {"Глобальная цель": "Dummy Goal"}


class DummyAsyncLLM(AsyncLLMInterface):
    # Add other LLMInterface methods as async stubs for interface compliance
    async def generate_motivation(self, goal_text: str, progress_summary: str) -> str:
        return "Async motivation!"

    async def generate_plan(
        self, goal_text: str, deadline: str, available: str
    ) -> List[Dict[str, Any]]:
        # Возвращаем простой план на 2 дня
        return [
            {"day": 1, "task": "Task 1"},
            {"day": 2, "task": "Task 2"},
        ]


@pytest.mark.asyncio
async def test_set_new_goal_async(monkeypatch):
    # Патчим форматирование даты/дня недели, чтобы результат был детерминирован
    monkeypatch.setattr(
        "core.goal_manager.format_date", lambda dt: "01.01.2025", raising=True
    )
    monkeypatch.setattr(
        "core.goal_manager.get_day_of_week", lambda dt: "Среда", raising=True
    )

    sheets = DummyAsyncSheets()
    llm = DummyAsyncLLM()
    gm = GoalManager(storage=sheets, llm=llm)

    url = await gm.set_new_goal(777, "Test goal", "30 дней", "1 час")

    assert url == "http://dummy_spreadsheet"
    # Проверяем, что данные сохранены
    assert sheets.calls["clear_user_data"] == 777
    assert sheets.calls["save_goal_info"][0] == 777
    saved_plan = sheets.calls["save_plan"][1]
    # Должно быть 2 строки плана
    assert len(saved_plan) == 2
    # Первая строка содержит ожидаемые поля
    first = saved_plan[0]
    assert first[COL_DATE] == "01.01.2025"
    assert first[COL_DAYOFWEEK] == "Среда"
    assert first[COL_TASK] == "Task 1"
    assert first[COL_STATUS] == "Не выполнено"
