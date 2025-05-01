import pytest

from core.goal_manager import GoalManager
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS


class DummyAsyncSheets:
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


class DummyAsyncLLM:
    async def generate_plan(
        self, goal_text: str, deadline: str, available: str
    ):  # noqa: D401
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
    gm = GoalManager(sheets_async=sheets, llm_async=llm)

    url = await gm.set_new_goal_async(777, "Test goal", "30 дней", "1 час")

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
