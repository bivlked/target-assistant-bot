import pytest

from core.goal_manager import GoalManager
from core.interfaces import StorageInterface, LLMInterface
from typing import cast


class DummySheets:
    """Мини-клиент, фиксирует аргументы и позволяет задавать ответы."""

    def __init__(self):
        self.last_params = {}
        # предустановленные ответы
        self._today_task = {"task": "dummy"}
        self._extended_stats = {
            "total_days": 1,
            "completed_days": 0,
            "progress_percent": 0,
            "days_passed": 0,
            "days_left": 1,
            "upcoming_tasks": [],
            "sheet_url": "http://sheet",
        }
        self._goal_info = {"Глобальная цель": "Выучить Python"}

    # методы, вызываемые GoalManager
    def get_task_for_date(self, user_id: int, target_date: str):  # noqa: D401
        self.last_params["get_task_for_date"] = (user_id, target_date)
        return self._today_task

    def get_extended_statistics(self, user_id: int, upcoming_count: int = 5):
        self.last_params["get_extended_statistics"] = (user_id, upcoming_count)
        return self._extended_stats

    def get_goal_info(self, user_id: int):
        self.last_params["get_goal_info"] = (user_id,)
        return self._goal_info


class DummyLLM:
    """Пустышка, чтобы не вызывать сеть."""

    def generate_motivation(self, *args, **kwargs):  # noqa: D401
        return "Stay strong!"


@pytest.fixture()
def goal_manager():
    sheets = DummySheets()
    llm = DummyLLM()
    # Cast dummy instances to interfaces for GoalManager constructor
    gm = GoalManager(
        sheets_sync=cast(StorageInterface, sheets), llm_sync=cast(LLMInterface, llm)
    )
    return gm, sheets


def test_get_today_task_uses_formatted_date(monkeypatch, goal_manager):
    gm, sheets = goal_manager

    # Зафиксируем дату, которую должен вернуть helpers.format_date
    monkeypatch.setattr(
        "core.goal_manager.format_date", lambda dt: "02.05.2025", raising=True
    )

    gm.get_today_task(user_id=42)

    # Sheets получил именно отформатированную дату
    assert sheets.last_params["get_task_for_date"] == (42, "02.05.2025")


def test_get_detailed_status_combines_data(goal_manager):
    gm, sheets = goal_manager
    res = gm.get_detailed_status(user_id=7)

    # Проверяем, что поле goal взято из goal_info
    assert res["goal"] == "Выучить Python"
    # Прогресс и url из stats
    assert res["sheet_url"] == "http://sheet"
    assert res["progress_percent"] == 0
