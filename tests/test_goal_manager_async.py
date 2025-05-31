"""Tests for the async GoalManager using AsyncStorageInterface and AsyncLLMInterface."""

import pytest
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from freezegun import freeze_time  # Добавлен импорт freeze_time

from core.goal_manager import (
    GoalManager,
    USER_FACING_STATUS_NOT_DONE,
    USER_FACING_STATUS_DONE,
    USER_FACING_STATUS_PARTIAL,
)
from core.interfaces import AsyncStorageInterface, AsyncLLMInterface
from core.models import Goal, Task, GoalPriority, GoalStatus, GoalStatistics, TaskStatus
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS
from utils.helpers import format_date as original_format_date_helper
from utils.helpers import get_day_of_week as original_get_day_of_week_helper
from utils.ratelimiter import RateLimitException
import structlog

logger = structlog.get_logger(__name__)


class DummyAsyncStorage(AsyncStorageInterface):
    """Dummy implementation of AsyncStorageInterface for testing."""

    def __init__(self):
        """Initializes the dummy storage."""
        self.calls: Dict[str, Any] = {}
        self.spreadsheet_url_to_return = "http://fake_url"
        self._mock_task_for_date = {}
        self._mock_stats_str = None
        self._mock_goal_info = None
        self._mock_extended_stats = None
        self._mock_active_goals = []

    async def create_spreadsheet(self, user_id: int) -> None:
        """Creates a spreadsheet for the user."""
        logger.debug("DummyAsyncStorage: create_spreadsheet called", user_id=user_id)
        self.calls["create_spreadsheet"] = user_id

    async def delete_spreadsheet(self, user_id: int) -> None:
        """Deletes the spreadsheet for the user."""
        logger.debug("DummyAsyncStorage: delete_spreadsheet called", user_id=user_id)
        self.calls["delete_spreadsheet"] = user_id

    async def clear_user_data(self, user_id: int) -> None:
        """Clears all user data."""
        logger.debug("DummyAsyncStorage: clear_user_data called", user_id=user_id)
        self.calls["clear_user_data"] = user_id

    async def get_active_goals(self, user_id: int) -> list:
        """Gets active goals for the user."""
        logger.debug("DummyAsyncStorage: get_active_goals called", user_id=user_id)
        self.calls["get_active_goals"] = user_id
        return self._mock_active_goals

    async def archive_goal(self, user_id: int, goal_id: int) -> None:
        """Archives a goal."""
        logger.debug(
            "DummyAsyncStorage: archive_goal called", user_id=user_id, goal_id=goal_id
        )
        self.calls[f"archive_goal_{user_id}_{goal_id}"] = True

    async def save_goal_info(self, user_id: int, goal: Goal) -> str:
        """Saves goal info and returns URL."""
        logger.debug("DummyAsyncStorage: save_goal_info called", user_id=user_id)
        # Convert Goal to dict for test compatibility
        info = {
            "Глобальная цель": goal.description,
            "Срок выполнения": goal.deadline,
            "Затраты в день": goal.daily_time,
            "Начало выполнения": goal.start_date,
        }
        self.calls["save_goal_info"] = user_id, info
        return self.spreadsheet_url_to_return

    async def save_plan(
        self, user_id: int, goal_id: int, plan: List[Dict[str, Any]]
    ) -> None:
        """Saves the plan."""
        logger.debug(
            "DummyAsyncStorage: save_plan called", user_id=user_id, goal_id=goal_id
        )
        self.calls["save_plan"] = user_id, plan

    async def save_goal_and_plan(
        self, user_id: int, goal_info: Dict[str, str], plan: List[Dict[str, Any]]
    ) -> str:
        """Saves goal info and plan together."""
        logger.debug("DummyAsyncStorage: save_goal_and_plan called", user_id=user_id)
        # Create a Goal object for save_goal_info
        goal = Goal(
            goal_id=1,
            name="Test Goal",
            description=goal_info.get("Глобальная цель", ""),
            deadline=goal_info.get("Срок выполнения", ""),
            daily_time=goal_info.get("Затраты в день", ""),
            start_date=goal_info.get("Начало выполнения", ""),
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.MEDIUM,
            tags=[],
        )
        await self.save_goal_info(user_id, goal)
        await self.save_plan(user_id, 1, plan)  # Use goal_id=1 for legacy compatibility
        return self.spreadsheet_url_to_return

    async def get_task_for_date(
        self, user_id: int, goal_id: int, date: str
    ) -> Optional[Task]:
        """Gets task for a specific date."""
        logger.debug(
            "DummyAsyncStorage: get_task_for_date called",
            user_id=user_id,
            goal_id=goal_id,
            date=date,
        )
        self.calls[f"get_task_for_date_{user_id}_{goal_id}_{date}"] = True
        task_dict = self._mock_task_for_date.get(date)
        if task_dict:
            # Convert dict to Task object
            status_str = task_dict.get(COL_STATUS, USER_FACING_STATUS_NOT_DONE)
            task_status = TaskStatus.NOT_DONE  # Default
            if status_str == USER_FACING_STATUS_DONE:
                task_status = TaskStatus.DONE
            elif status_str == USER_FACING_STATUS_PARTIAL:
                task_status = TaskStatus.PARTIALLY_DONE

            return Task(
                date=task_dict.get(COL_DATE, date),
                day_of_week=task_dict.get(COL_DAYOFWEEK, ""),
                task=task_dict.get(COL_TASK, ""),
                status=task_status,
                goal_id=goal_id,
                goal_name="",
            )
        return None

    async def get_task_for_today(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Gets task for today."""
        from utils.helpers import format_date
        from datetime import datetime

        today = format_date(datetime.now())
        logger.debug(
            "DummyAsyncStorage: get_task_for_today called", user_id=user_id, today=today
        )
        self.calls[f"get_task_for_date_{user_id}_{today}"] = True
        return self._mock_task_for_date.get(today)

    async def update_task_status(
        self, user_id: int, goal_id: int, date: str, status: str
    ) -> None:
        """Updates task status."""
        logger.debug(
            "DummyAsyncStorage: update_task_status called",
            user_id=user_id,
            goal_id=goal_id,
            date=date,
            status=status,
        )
        self.calls[f"update_task_status_{user_id}_{goal_id}_{date}_{status}"] = True

    async def update_task_status_old(
        self, user_id: int, date: str, status: str
    ) -> None:
        """Updates task status (legacy method)."""
        logger.debug(
            "DummyAsyncStorage: update_task_status_old called",
            user_id=user_id,
            date=date,
            status=status,
        )
        self.calls[f"update_task_status_{user_id}_{date}_{status}"] = True

    async def batch_update_task_statuses(
        self, user_id: int, updates: Dict[tuple[int, str], str]
    ) -> None:
        """Batch updates task statuses."""
        logger.debug(
            "DummyAsyncStorage: batch_update_task_statuses called", user_id=user_id
        )
        # Convert back to legacy format for test compatibility
        legacy_updates = {date: status for (goal_id, date), status in updates.items()}
        self.calls["batch_update_task_statuses"] = {
            "user_id": user_id,
            "updates": legacy_updates,
        }

    async def get_statistics(self, user_id: int) -> str:
        """Gets statistics."""
        logger.debug("DummyAsyncStorage: get_statistics called", user_id=user_id)
        self.calls[f"get_statistics_{user_id}"] = True
        if self._mock_stats_str is not None:
            return self._mock_stats_str
        return "Default stats"

    async def get_status_message(self, user_id: int) -> str:
        """Gets status message (alias for get_statistics)."""
        return await self.get_statistics(user_id)

    async def get_extended_statistics(
        self, user_id: int, count: int = 7
    ) -> Dict[str, Any]:
        """Gets extended statistics."""
        logger.debug(
            "DummyAsyncStorage: get_extended_statistics called",
            user_id=user_id,
            count=count,
        )
        self.calls[f"get_extended_statistics_{user_id}"] = True
        if self._mock_extended_stats is not None:
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

    async def get_goal_info(self, user_id: int) -> Dict[str, str]:
        """Gets goal info."""
        logger.debug("DummyAsyncStorage: get_goal_info called", user_id=user_id)
        self.calls[f"get_goal_info_{user_id}"] = True
        if self._mock_goal_info is not None:
            return self._mock_goal_info
        return {}

    async def get_all_goals(self, user_id: int) -> List[Goal]:
        """Get all goals for a user."""
        logger.debug("DummyAsyncStorage: get_all_goals called", user_id=user_id)
        self.calls["get_all_goals"] = user_id
        return self._mock_active_goals

    async def get_goal_by_id(self, user_id: int, goal_id: int) -> Optional[Goal]:
        """Get a specific goal by ID."""
        logger.debug(
            "DummyAsyncStorage: get_goal_by_id called", user_id=user_id, goal_id=goal_id
        )
        self.calls[f"get_goal_by_id_{user_id}_{goal_id}"] = True
        for goal in self._mock_active_goals:
            if goal.goal_id == goal_id:
                return goal
        return None

    async def get_active_goals_count(self, user_id: int) -> int:
        """Count active goals."""
        logger.debug(
            "DummyAsyncStorage: get_active_goals_count called", user_id=user_id
        )
        self.calls["get_active_goals_count"] = user_id
        return len(self._mock_active_goals)

    async def get_next_goal_id(self, user_id: int) -> int:
        """Get next available goal ID."""
        logger.debug("DummyAsyncStorage: get_next_goal_id called", user_id=user_id)
        self.calls["get_next_goal_id"] = user_id
        return len(self._mock_active_goals) + 1

    async def update_goal_status(
        self, user_id: int, goal_id: int, status: GoalStatus
    ) -> None:
        """Update goal status."""
        logger.debug(
            "DummyAsyncStorage: update_goal_status called",
            user_id=user_id,
            goal_id=goal_id,
            status=status,
        )
        self.calls[f"update_goal_status_{user_id}_{goal_id}_{status}"] = True

    async def update_goal_progress(
        self, user_id: int, goal_id: int, progress: int
    ) -> None:
        """Update goal progress percentage."""
        logger.debug(
            "DummyAsyncStorage: update_goal_progress called",
            user_id=user_id,
            goal_id=goal_id,
            progress=progress,
        )
        self.calls[f"update_goal_progress_{user_id}_{goal_id}_{progress}"] = True

    async def update_goal_priority(
        self, user_id: int, goal_id: int, priority: GoalPriority
    ) -> None:
        """Update goal priority."""
        logger.debug(
            "DummyAsyncStorage: update_goal_priority called",
            user_id=user_id,
            goal_id=goal_id,
            priority=priority,
        )
        self.calls[f"update_goal_priority_{user_id}_{goal_id}_{priority}"] = True

    async def delete_goal(self, user_id: int, goal_id: int) -> None:
        """Delete a goal completely."""
        logger.debug(
            "DummyAsyncStorage: delete_goal called", user_id=user_id, goal_id=goal_id
        )
        self.calls[f"delete_goal_{user_id}_{goal_id}"] = True

    async def get_plan_for_goal(self, user_id: int, goal_id: int) -> List[Task]:
        """Get plan for a specific goal."""
        logger.debug(
            "DummyAsyncStorage: get_plan_for_goal called",
            user_id=user_id,
            goal_id=goal_id,
        )
        self.calls[f"get_plan_for_goal_{user_id}_{goal_id}"] = True
        return []

    async def get_all_tasks_for_date(self, user_id: int, date: str) -> List[Task]:
        """Get all tasks for a specific date."""
        logger.debug(
            "DummyAsyncStorage: get_all_tasks_for_date called",
            user_id=user_id,
            date=date,
        )
        self.calls[f"get_all_tasks_for_date_{user_id}_{date}"] = True
        return []

    async def get_goal_statistics(self, user_id: int, goal_id: int) -> GoalStatistics:
        """Get statistics for a specific goal."""
        logger.debug(
            "DummyAsyncStorage: get_goal_statistics called",
            user_id=user_id,
            goal_id=goal_id,
        )
        self.calls[f"get_goal_statistics_{user_id}_{goal_id}"] = True
        return GoalStatistics(
            total_tasks=0,
            completed_tasks=0,
            progress_percent=0,
            days_elapsed=0,
            days_remaining=0,
            completion_rate=0.0,
        )

    async def get_overall_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get overall statistics for all goals."""
        logger.debug(
            "DummyAsyncStorage: get_overall_statistics called", user_id=user_id
        )
        self.calls[f"get_overall_statistics_{user_id}"] = True
        return {}


class DummyAsyncLLM(AsyncLLMInterface):
    """Mock implementation of AsyncLLMInterface for testing GoalManager."""

    def __init__(self):
        """Initializes the mock LLM, tracking method calls."""
        self.calls: Dict[str, Any] = {}
        self.plan_to_return: List[Dict[str, Any]] = [
            {"day": 1, "task": "Default Task 1"},
            {"day": 2, "task": "Default Task 2"},
        ]
        self.motivation_to_return: str = "Default async motivation!"

    async def generate_plan(
        self,
        goal_text: str,
        deadline: str,
        time: str,  # Renamed 'available' to 'time' for consistency
    ) -> List[Dict[str, Any]]:
        """(Mock) Simulates generating a task plan."""
        self.calls[f"generate_plan_{goal_text}_{deadline}_{time}"] = True
        return self.plan_to_return  # Return a predefined plan

    async def generate_motivation(self, goal_text: str, progress_summary: str) -> str:
        """(Mock) Simulates generating a motivational message."""
        self.calls[f"generate_motivation_{goal_text}_{progress_summary}"] = True
        return self.motivation_to_return


class MockUserRateLimiter:
    """Mock for UserRateLimiter to control its behavior in tests."""

    def __init__(self, should_raise: bool = False, retry_after: Optional[float] = None):
        self.should_raise = should_raise
        self.retry_after = retry_after
        self.check_limit_called_with: List[Tuple[Any, int]] = []

    def check_limit(self, user_id: Any, tokens_to_consume: int = 1) -> None:
        self.check_limit_called_with.append((user_id, tokens_to_consume))
        if self.should_raise:
            raise RateLimitException(
                "Mock rate limit exceeded", retry_after_seconds=self.retry_after
            )
        # Otherwise, do nothing (limit not exceeded)


@pytest.mark.asyncio
@freeze_time("2025-01-10 00:00:00+00:00")  # Оставляем декоратор
async def test_set_new_goal_async(monkeypatch: pytest.MonkeyPatch):
    """Tests the set_new_goal method of GoalManager, including date calculations."""

    frozen_today = datetime(2025, 1, 10, 0, 0, 0, tzinfo=timezone.utc)

    format_date_args_recorder: List[datetime] = []
    get_day_of_week_args_recorder: List[datetime] = []

    # Моки format_date и get_day_of_week
    def mock_format_date_for_gm(date_obj: datetime, tz: Optional[str] = None) -> str:
        # print(f"DEBUG [mock_format_date_for_gm] CALLED with {date_obj}") # Убираем print из мока
        format_date_args_recorder.append(date_obj)
        return original_format_date_helper(date_obj, "UTC")

    def mock_get_day_of_week_for_gm(
        date_obj: datetime, tz: Optional[str] = None
    ) -> str:
        get_day_of_week_args_recorder.append(date_obj)
        return original_get_day_of_week_helper(date_obj, "UTC")

    monkeypatch.setattr("core.goal_manager.format_date", mock_format_date_for_gm)
    monkeypatch.setattr(
        "core.goal_manager.get_day_of_week", mock_get_day_of_week_for_gm
    )

    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)

    llm_mock.plan_to_return = [
        {"day": 1, "task": "Task for day 1"},
        {"day": 3, "task": "Task for day 3"},
        {"day": 5, "task": "Task for day 5"},
    ]
    storage_mock.spreadsheet_url_to_return = "http://dynamic_date_test_url"

    user_id = 777
    goal_text = "Test goal with dynamic dates"
    deadline_str = "за 5 дней"
    available_time_str = "1 час в день"

    url = await gm.set_new_goal(user_id, goal_text, deadline_str, available_time_str)

    assert url == "http://dynamic_date_test_url"

    # Проверяем, что format_date и get_day_of_week вызывались правильное количество раз
    assert len(format_date_args_recorder) == 3 + 1  # 3 для плана, 1 для goal_info
    assert len(get_day_of_week_args_recorder) == 3  # 3 для плана

    # Проверяем даты, переданные в format_date (в порядке их вызова в GoalManager)
    # Порядок: сначала все элементы плана, потом goal_info['Начало выполнения']
    assert format_date_args_recorder[0] == (
        frozen_today + timedelta(days=0)
    )  # План: день 1 (offset 0)
    assert format_date_args_recorder[1] == (
        frozen_today + timedelta(days=2)
    )  # План: день 3 (offset 2)
    assert format_date_args_recorder[2] == (
        frozen_today + timedelta(days=4)
    )  # План: день 5 (offset 4)
    assert format_date_args_recorder[3] == frozen_today  # goal_info: Начало выполнения

    # Проверяем даты, переданные в get_day_of_week (только для плана)
    assert get_day_of_week_args_recorder[0] == (frozen_today + timedelta(days=0))
    assert get_day_of_week_args_recorder[1] == (frozen_today + timedelta(days=2))
    assert get_day_of_week_args_recorder[2] == (frozen_today + timedelta(days=4))

    # Проверка сохраненных данных
    saved_goal_info = storage_mock.calls["save_goal_info"][1]
    assert saved_goal_info["Начало выполнения"] == original_format_date_helper(
        frozen_today, "UTC"
    )

    saved_plan = storage_mock.calls["save_plan"][1]
    assert len(saved_plan) == 3
    assert saved_plan[0][COL_DATE] == original_format_date_helper(
        frozen_today + timedelta(days=0), "UTC"
    )
    assert saved_plan[1][COL_DATE] == original_format_date_helper(
        frozen_today + timedelta(days=2), "UTC"
    )
    assert saved_plan[2][COL_DATE] == original_format_date_helper(
        frozen_today + timedelta(days=4), "UTC"
    )
    # ... и другие ассерты для saved_plan (дни недели, задачи, статусы) ...


@pytest.mark.asyncio
async def test_get_today_task_found(monkeypatch: pytest.MonkeyPatch):
    """Tests get_today_task when a task for today exists."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)

    user_id = 123
    today_date_str = "02.01.2025"
    expected_task = {
        COL_DATE: today_date_str,
        COL_DAYOFWEEK: "Четверг",
        COL_TASK: "Today's test task",
        COL_STATUS: USER_FACING_STATUS_NOT_DONE,
    }
    storage_mock._mock_task_for_date = {today_date_str: expected_task}

    # Patch format_date to return a fixed string for today
    monkeypatch.setattr("core.goal_manager.format_date", lambda dt: today_date_str)

    task = await gm.get_today_task(user_id)

    assert task == expected_task
    assert f"get_task_for_date_{user_id}_{today_date_str}" in storage_mock.calls


@pytest.mark.asyncio
async def test_get_today_task_not_found(monkeypatch: pytest.MonkeyPatch):
    """Tests get_today_task when no task for today exists."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)

    user_id = 456
    today_date_str = "03.01.2025"
    storage_mock._mock_task_for_date = {}  # Ensure no task for this date

    monkeypatch.setattr("core.goal_manager.format_date", lambda dt: today_date_str)

    task = await gm.get_today_task(user_id)

    assert task is None
    assert f"get_task_for_date_{user_id}_{today_date_str}" in storage_mock.calls


@pytest.mark.asyncio
async def test_update_today_task_status(monkeypatch: pytest.MonkeyPatch):
    """Tests update_today_task_status."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)

    user_id = 789
    today_date_str = "04.01.2025"
    new_status = USER_FACING_STATUS_DONE

    # Mock the TASKS_STATUS_UPDATED_TOTAL metric
    class MockCounter:
        def __init__(self):
            self.called_with = None

        def labels(self, new_status):
            self.called_with = new_status
            return self  # Return self to allow .inc()

        def inc(self):
            pass  # No actual increment needed for this test logic

    mock_metric = MockCounter()
    monkeypatch.setattr("core.goal_manager.TASKS_STATUS_UPDATED_TOTAL", mock_metric)
    monkeypatch.setattr("core.goal_manager.format_date", lambda dt: today_date_str)
    # Patch the status mapping in goal_manager if it's used before metric.labels
    # (it is, so we need to ensure our Russian status maps to an English one for the metric)
    monkeypatch.setattr(
        "core.goal_manager.RUSSIAN_TO_ENGLISH_STATUS_MAP",
        {
            USER_FACING_STATUS_DONE: "DONE",
            USER_FACING_STATUS_NOT_DONE: "NOT_DONE",
            USER_FACING_STATUS_PARTIAL: "PARTIALLY_DONE",
        },
    )

    await gm.update_today_task_status(user_id, new_status)

    # Check that storage method was called correctly
    assert storage_mock.calls[
        f"update_task_status_{user_id}_{today_date_str}_{new_status}"
    ]
    # Check that metric was called with the (mapped) English status
    assert mock_metric.called_with == "DONE"


@pytest.mark.asyncio
async def test_get_goal_status_details():
    """Tests get_goal_status_details calls storage.get_statistics."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)
    user_id = 111

    expected_stats_str = "Simple stats: 5/10 done via mock attribute."
    storage_mock._mock_stats_str = expected_stats_str

    result = await gm.get_goal_status_details(user_id)

    assert result == expected_stats_str
    assert storage_mock.calls.get(f"get_statistics_{user_id}")


@pytest.mark.asyncio
async def test_get_detailed_status(monkeypatch: pytest.MonkeyPatch):
    """Tests get_detailed_status correctly combines info from storage."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)
    user_id = 222
    mock_goal_data = {"Глобальная цель": "Conquer the world via attribute"}
    mock_ext_stats_data = {
        "total_days": 100,
        "completed_days": 50,
        "progress_percent": 50,
    }

    storage_mock._mock_goal_info = mock_goal_data
    storage_mock._mock_extended_stats = mock_ext_stats_data

    result = await gm.get_detailed_status(user_id)
    expected_result = {"goal": "Conquer the world via attribute", **mock_ext_stats_data}
    assert result == expected_result
    assert storage_mock.calls.get(f"get_extended_statistics_{user_id}")
    assert storage_mock.calls.get(f"get_goal_info_{user_id}")


@pytest.mark.asyncio
async def test_generate_motivation_message(monkeypatch: pytest.MonkeyPatch):
    """Tests generate_motivation_message."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)
    user_id = 333

    mock_goal_text = "Learn to fly via attribute"
    mock_stats_str = "Overall progress: Good via attribute"
    expected_motivation = "You can do it! Fly high! Attribute version!"

    storage_mock._mock_goal_info = {"Глобальная цель": mock_goal_text}
    storage_mock._mock_stats_str = mock_stats_str
    llm_mock.motivation_to_return = expected_motivation

    # Используем наш MockUserRateLimiter, определенный выше в файле
    actual_mock_limiter = MockUserRateLimiter(
        should_raise=False
    )  # Был просто MockRateLimiter()
    gm.llm_rate_limiter = actual_mock_limiter  # type: ignore[assignment]

    result = await gm.generate_motivation_message(user_id)

    assert result == expected_motivation
    assert storage_mock.calls.get(f"get_goal_info_{user_id}")
    assert storage_mock.calls.get(f"get_statistics_{user_id}")
    assert llm_mock.calls.get(f"generate_motivation_{mock_goal_text}_{mock_stats_str}")
    assert len(actual_mock_limiter.check_limit_called_with) == 1
    assert actual_mock_limiter.check_limit_called_with[0] == (user_id, 1)


@pytest.mark.asyncio
async def test_setup_user():
    """Tests setup_user calls storage.create_spreadsheet."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)
    user_id = 444

    await gm.setup_user(user_id)
    assert storage_mock.calls["create_spreadsheet"] == user_id


@pytest.mark.asyncio
async def test_reset_user():
    """Tests reset_user calls storage.delete_spreadsheet."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)
    user_id = 555

    await gm.reset_user(user_id)
    assert storage_mock.calls["delete_spreadsheet"] == user_id


@pytest.mark.asyncio
async def test_batch_update_task_statuses(monkeypatch: pytest.MonkeyPatch):
    """Tests batch_update_task_statuses."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)
    user_id = 666
    updates = {
        "05.01.2025": USER_FACING_STATUS_DONE,
        "06.01.2025": USER_FACING_STATUS_PARTIAL,
    }

    # Mock the TASKS_STATUS_UPDATED_TOTAL metric
    class MockCounter:
        def __init__(self):
            self.called_with_statuses: List[str] = []

        def labels(self, new_status):
            self.called_with_statuses.append(new_status)
            return self  # Return self to allow .inc()

        def inc(self):
            pass

    mock_metric = MockCounter()
    monkeypatch.setattr("core.goal_manager.TASKS_STATUS_UPDATED_TOTAL", mock_metric)
    # Patch the status mapping
    monkeypatch.setattr(
        "core.goal_manager.RUSSIAN_TO_ENGLISH_STATUS_MAP",
        {
            USER_FACING_STATUS_DONE: "DONE",
            USER_FACING_STATUS_NOT_DONE: "NOT_DONE",
            USER_FACING_STATUS_PARTIAL: "PARTIALLY_DONE",
        },
    )

    await gm.batch_update_task_statuses(user_id, updates)

    # assert storage_mock.calls[("batch_update_task_statuses", user_id, updates)] # Old assertion
    call_info = storage_mock.calls.get("batch_update_task_statuses")
    assert call_info is not None
    assert call_info["user_id"] == user_id
    assert call_info["updates"] == updates
    assert sorted(mock_metric.called_with_statuses) == sorted(
        ["DONE", "PARTIALLY_DONE"]
    )


@pytest.mark.asyncio
async def test_set_new_goal_rate_limited(monkeypatch: pytest.MonkeyPatch):
    """Tests that set_new_goal handles RateLimitException from llm_rate_limiter."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()  # LLM не должен быть вызван
    gm = GoalManager(storage=storage_mock, llm=llm_mock)

    user_id = 888
    # Настраиваем мок RateLimiter на выбрасывание исключения
    mock_limiter = MockUserRateLimiter(should_raise=True, retry_after=5.0)
    gm.llm_rate_limiter = mock_limiter  # type: ignore[assignment]

    with pytest.raises(RateLimitException) as excinfo:
        await gm.set_new_goal(user_id, "Rate limited goal", "10 дней", "1 час")

    assert excinfo.value.retry_after_seconds == 5.0
    assert len(mock_limiter.check_limit_called_with) == 1
    assert mock_limiter.check_limit_called_with[0] == (
        user_id,
        1,
    )  # По умолчанию 1 токен

    # Убедимся, что clear_user_data был вызван до проверки лимита
    assert storage_mock.calls.get("clear_user_data") == user_id
    # Убедимся, что llm.generate_plan и последующие вызовы storage не были сделаны
    assert not any(call_key[0] == "generate_plan" for call_key in llm_mock.calls)
    assert "save_goal_info" not in storage_mock.calls
    assert "save_plan" not in storage_mock.calls


@pytest.mark.asyncio
async def test_set_new_goal_rate_limit_not_exceeded(monkeypatch: pytest.MonkeyPatch):
    """Tests set_new_goal proceeds normally when rate limit is not exceeded."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)

    mock_limiter = MockUserRateLimiter(should_raise=False)
    gm.llm_rate_limiter = mock_limiter  # type: ignore[assignment]

    monkeypatch.setattr("core.goal_manager.format_date", lambda dt: "01.01.2025")
    monkeypatch.setattr("core.goal_manager.get_day_of_week", lambda dt: "Среда")

    user_id = 999
    await gm.set_new_goal(user_id, "Not rate limited goal", "5 дней", "30 мин")

    assert len(mock_limiter.check_limit_called_with) == 1
    assert mock_limiter.check_limit_called_with[0] == (user_id, 1)
    assert "save_plan" in storage_mock.calls  # Убедимся, что основной поток выполнился


@pytest.mark.asyncio
async def test_generate_motivation_rate_limited(monkeypatch: pytest.MonkeyPatch):
    """Tests that generate_motivation_message handles RateLimitException."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)
    user_id = 101

    mock_limiter = MockUserRateLimiter(should_raise=True, retry_after=3.0)
    gm.llm_rate_limiter = mock_limiter  # type: ignore[assignment]

    # Моки для вызовов storage, которые происходят до вызова LLM
    storage_mock._mock_goal_info = {"Глобальная цель": "Be awesome"}

    async def temp_get_stats(user_id: int) -> str:
        return "Looking good"

    monkeypatch.setattr(storage_mock, "get_statistics", temp_get_stats)

    with pytest.raises(RateLimitException) as excinfo:
        await gm.generate_motivation_message(user_id)

    assert excinfo.value.retry_after_seconds == 3.0
    assert len(mock_limiter.check_limit_called_with) == 1
    assert mock_limiter.check_limit_called_with[0] == (user_id, 1)
    # Убедимся, что generate_motivation не был вызван у LLM
    assert not any(call_key[0] == "generate_motivation" for call_key in llm_mock.calls)


@pytest.mark.asyncio
async def test_generate_motivation_rate_limit_not_exceeded(
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests generate_motivation_message proceeds normally when rate limit is not exceeded."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)
    user_id = 102

    mock_limiter = MockUserRateLimiter(should_raise=False)
    gm.llm_rate_limiter = mock_limiter  # type: ignore[assignment]

    mock_goal_data = {"Глобальная цель": "Be more awesome"}
    mock_stats_str = "Still looking good"
    expected_motivation = "You are indeed more awesome!"

    storage_mock._mock_goal_info = mock_goal_data

    async def temp_get_stats(user_id: int) -> str:
        return mock_stats_str

    monkeypatch.setattr(storage_mock, "get_statistics", temp_get_stats)
    llm_mock.motivation_to_return = expected_motivation

    result = await gm.generate_motivation_message(user_id)

    assert result == expected_motivation
    assert len(mock_limiter.check_limit_called_with) == 1
    assert mock_limiter.check_limit_called_with[0] == (user_id, 1)
    assert (
        f"generate_motivation_{mock_goal_data['Глобальная цель']}_{mock_stats_str}"
        in llm_mock.calls
    )


@pytest.mark.asyncio
async def test_get_detailed_status_no_goal_info():
    """Tests get_detailed_status when goal_info is missing or empty."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)
    user_id = 223

    storage_mock._mock_goal_info = {}  # Устанавливаем пустой словарь через атрибут

    # get_extended_statistics вернет дефолтное значение из DummyAsyncStorage,
    # которое мы там определили. Можно его явно получить для сравнения.
    default_ext_stats_shape = {
        "total_days": 0,
        "completed_days": 0,
        "progress_percent": 0,
        "days_passed": 0,
        "days_left": 0,
        "upcoming_tasks": [],
        "sheet_url": "",
    }
    storage_mock._mock_extended_stats = (
        default_ext_stats_shape  # Явно установим, чтобы быть уверенными
    )

    result = await gm.get_detailed_status(user_id)

    expected_result = {"goal": "—", **default_ext_stats_shape}
    assert result == expected_result
    assert storage_mock.calls.get(f"get_extended_statistics_{user_id}")
    assert storage_mock.calls.get(f"get_goal_info_{user_id}")


@pytest.mark.asyncio
async def test_get_detailed_status_default_stats():
    """Tests get_detailed_status with default (empty) extended_statistics."""
    storage_mock = DummyAsyncStorage()
    llm_mock = DummyAsyncLLM()
    gm = GoalManager(storage=storage_mock, llm=llm_mock)
    user_id = 224

    mock_goal_data = {"Глобальная цель": "Specific Goal for Test"}
    # Ensure extended_stats returns its default empty-like structure
    default_ext_stats = {
        "total_days": 0,
        "completed_days": 0,
        "progress_percent": 0,
        "days_passed": 0,
        "days_left": 0,
        "upcoming_tasks": [],
        "sheet_url": "",
    }
    storage_mock._mock_goal_info = mock_goal_data
    storage_mock._mock_extended_stats = default_ext_stats  # Set to default

    result = await gm.get_detailed_status(user_id)

    expected_result = {"goal": "Specific Goal for Test", **default_ext_stats}
    assert result == expected_result
