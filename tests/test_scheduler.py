"""Tests for the Scheduler and its job scheduling logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from scheduler.tasks import Scheduler
from core.models import Goal, Task, TaskStatus, GoalPriority, GoalStatus, GoalStatistics
from utils.helpers import format_date


class DummyAsyncStorage:
    """A mock AsyncStorageInterface for testing the Scheduler."""

    def __init__(self):
        """Initializes the mock, tracking called methods."""
        self.called: dict[str, any] = {}
        self.goals = []
        self.tasks = []

    async def get_all_tasks_for_date(self, user_id: int, date: str) -> list[Task]:
        """Simulates fetching all tasks for a specific date."""
        self.called["get_all_tasks_for_date"] = (user_id, date)
        return self.tasks

    async def get_active_goals(self, user_id: int) -> list[Goal]:
        """Simulates fetching active goals."""
        self.called["get_active_goals"] = user_id
        return self.goals

    async def get_goal_statistics(self, user_id: int, goal_id: int) -> GoalStatistics:
        """Simulates fetching goal statistics."""
        self.called[f"get_goal_statistics_{goal_id}"] = user_id
        return GoalStatistics(
            total_tasks=10,
            completed_tasks=5,
            progress_percent=50,
            days_elapsed=15,
            days_remaining=15,
            completion_rate=0.5,
        )


class DummyAsyncLLM:
    """A mock AsyncLLMInterface for testing the Scheduler."""

    def __init__(self):
        """Initializes the mock."""
        self.called: dict[str, any] = {}

    async def generate_motivation(self, goal_info: str, progress_summary: str) -> str:
        """Simulates generating a motivational message."""
        self.called["generate_motivation"] = (goal_info, progress_summary)
        return "Keep going! Mocked motivation!"


class DummyBot:
    """A mock Telegram Bot for testing message sending."""

    def __init__(self):
        """Initializes the mock, tracking sent messages."""
        self.sent = []

    async def send_message(self, **kwargs):
        """Simulates sending a message."""
        self.sent.append(kwargs)


# Mock is_subscribed to always return True for tests
@pytest.fixture(autouse=True)
def mock_is_subscribed(monkeypatch):
    """Mock is_subscribed to always return True."""

    async def always_subscribed(user_id):
        return True

    monkeypatch.setattr("scheduler.tasks.is_subscribed", always_subscribed)


@pytest.fixture()
def scheduler_instance():
    """Provides a Scheduler instance with mock storage and llm for tests."""
    storage = DummyAsyncStorage()
    llm = DummyAsyncLLM()
    return Scheduler(storage, llm), storage, llm


@pytest.mark.asyncio
async def test_add_user_jobs(scheduler_instance):
    """Tests that user-specific jobs are correctly added to APScheduler."""
    import asyncio

    sched, _, _ = scheduler_instance

    # Initialize scheduler with current event loop by calling start()
    sched._event_loop = asyncio.get_running_loop()
    sched.start()

    bot = DummyBot()
    sched.add_user_jobs(bot, 123)
    jobs = {j.id for j in sched.scheduler.get_jobs()}
    assert jobs == {"morning_123", "evening_123", "motivation_123"}


@pytest.mark.asyncio
async def test_send_today_task_task_exists(scheduler_instance, monkeypatch):
    """Tests the _send_today_tasks job logic when tasks for today exist."""
    sched, storage, _ = scheduler_instance
    bot = DummyBot()
    user_id = 555

    # Create test tasks - fixed to use correct parameters
    test_task = Task(
        date="15.05.2025",
        day_of_week="Четверг",
        task="Scheduled Test Task",
        status=TaskStatus.NOT_DONE,
        goal_id=1,
        goal_name="Test Goal",
    )
    storage.tasks = [test_task]

    # Mock format_date to return our test date
    monkeypatch.setattr("scheduler.tasks.format_date", lambda x: "15.05.2025")

    await sched._send_today_tasks(bot, user_id)

    assert storage.called["get_all_tasks_for_date"] == (user_id, "15.05.2025")
    assert len(bot.sent) == 1
    assert "Test Goal" in bot.sent[0]["text"]
    assert "Scheduled Test Task" in bot.sent[0]["text"]
    assert bot.sent[0]["chat_id"] == user_id


@pytest.mark.asyncio
async def test_send_today_task_no_task(scheduler_instance, monkeypatch):
    """Tests the _send_today_tasks job logic when no tasks for today exist."""
    sched, storage, _ = scheduler_instance
    bot = DummyBot()
    user_id = 556

    # No tasks
    storage.tasks = []

    # Mock format_date
    monkeypatch.setattr("scheduler.tasks.format_date", lambda x: "15.05.2025")

    await sched._send_today_tasks(bot, user_id)

    assert storage.called["get_all_tasks_for_date"] == (user_id, "15.05.2025")
    assert len(bot.sent) == 1
    assert "На сегодня у вас нет запланированных задач" in bot.sent[0]["text"]
    assert bot.sent[0]["chat_id"] == user_id


@pytest.mark.asyncio
async def test_send_evening_reminder(scheduler_instance, monkeypatch):
    """Tests the _send_evening_reminder job logic."""
    sched, storage, _ = scheduler_instance
    bot = DummyBot()
    user_id = 557

    # Create incomplete task - fixed to use correct parameters
    test_task = Task(
        date="15.05.2025",
        day_of_week="Четверг",
        task="Evening Task",
        status=TaskStatus.NOT_DONE,
        goal_id=1,
        goal_name="Test Goal",
    )
    storage.tasks = [test_task]

    # Mock format_date
    monkeypatch.setattr("scheduler.tasks.format_date", lambda x: "15.05.2025")

    await sched._send_evening_reminder(bot, user_id)

    assert len(bot.sent) == 1
    assert "Доброй ночи! Не забудьте отметить прогресс" in bot.sent[0]["text"]
    assert bot.sent[0]["chat_id"] == user_id


@pytest.mark.asyncio
async def test_send_motivation(scheduler_instance):
    """Tests the _send_motivation job logic."""
    sched, storage, llm = scheduler_instance
    bot = DummyBot()
    user_id = 777

    # Create test goal
    test_goal = Goal(
        goal_id=1,
        name="Test Goal",
        description="Learn Python",
        deadline="01.06.2025",
        daily_time="1 час",
        start_date="01.05.2025",
        status=GoalStatus.ACTIVE,
        priority=GoalPriority.HIGH,
        tags=["education"],
    )
    storage.goals = [test_goal]

    await sched._send_motivation(bot, user_id)

    assert storage.called["get_active_goals"] == user_id
    assert "generate_motivation" in llm.called
    assert len(bot.sent) == 1
    assert "Keep going! Mocked motivation!" in bot.sent[0]["text"]
    assert bot.sent[0]["chat_id"] == user_id
