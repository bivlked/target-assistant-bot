"""Enhanced tests for Scheduler to achieve 97% coverage.

Focus on edge cases and error scenarios not covered by basic tests.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from scheduler.tasks import Scheduler
from core.models import Goal, Task, TaskStatus, GoalPriority, GoalStatus, GoalStatistics
from utils.helpers import format_date


class MockAsyncStorage:
    """Enhanced mock AsyncStorageInterface for edge case testing."""

    def __init__(self):
        self.called = {}
        self.goals = []
        self.tasks = []
        self.should_raise = False

    async def get_all_tasks_for_date(self, user_id: int, date: str) -> list[Task]:
        self.called["get_all_tasks_for_date"] = (user_id, date)
        if self.should_raise:
            raise Exception("Mocked storage error")
        return self.tasks

    async def get_active_goals(self, user_id: int) -> list[Goal]:
        self.called["get_active_goals"] = user_id
        if self.should_raise:
            raise Exception("Mocked storage error")
        return self.goals

    async def get_goal_statistics(self, user_id: int, goal_id: int) -> GoalStatistics:
        self.called[f"get_goal_statistics_{goal_id}"] = user_id
        if self.should_raise:
            raise Exception("Mocked storage error")
        return GoalStatistics(
            total_tasks=10,
            completed_tasks=8,
            progress_percent=80,
            days_elapsed=20,
            days_remaining=10,
            completion_rate=0.8,
        )


class MockAsyncLLM:
    """Enhanced mock AsyncLLMInterface for edge case testing."""

    def __init__(self):
        self.called = {}
        self.should_raise = False

    async def generate_motivation(self, goal_info: str, progress_summary: str) -> str:
        self.called["generate_motivation"] = (goal_info, progress_summary)
        if self.should_raise:
            raise Exception("Mocked LLM error")
        return "Enhanced motivation message!"


class MockBot:
    """Enhanced mock Telegram Bot for testing message sending."""

    def __init__(self):
        self.sent = []
        self.should_raise = False

    async def send_message(self, **kwargs):
        if self.should_raise:
            raise Exception("Mocked bot error")
        self.sent.append(kwargs)


@pytest.fixture()
def enhanced_scheduler():
    """Provides enhanced Scheduler with mocks for edge case testing."""
    storage = MockAsyncStorage()
    llm = MockAsyncLLM()
    return Scheduler(storage, llm), storage, llm


@pytest.mark.asyncio
async def test_scheduler_initialization_without_event_loop():
    """Test scheduler initialization edge case when no event loop is running."""
    storage = MockAsyncStorage()
    llm = MockAsyncLLM()

    # Create scheduler without event loop
    scheduler = Scheduler(storage, llm, event_loop=None)

    # Mock asyncio.get_running_loop to raise RuntimeError
    with patch("asyncio.get_running_loop", side_effect=RuntimeError("No running loop")):
        # This should handle the error gracefully (covers line 103-104)
        scheduler.start()

    # Scheduler should not be initialized due to missing event loop
    assert scheduler.scheduler is None


@pytest.mark.asyncio
async def test_add_user_jobs_with_no_scheduler():
    """Test add_user_jobs when scheduler is not initialized (covers line 148)."""
    storage = MockAsyncStorage()
    llm = MockAsyncLLM()
    scheduler = Scheduler(storage, llm)

    # Don't call start(), so scheduler.scheduler remains None
    bot = MockBot()

    # This should handle the case where scheduler is None gracefully
    scheduler.add_user_jobs(bot, 123)

    # Should not crash and not add any jobs
    assert scheduler.scheduler is None


@pytest.mark.asyncio
async def test_send_today_tasks_all_completed(enhanced_scheduler, monkeypatch):
    """Test _send_today_tasks when all tasks are completed (covers line 163-167)."""
    sched, storage, _ = enhanced_scheduler
    bot = MockBot()
    user_id = 999

    # Create completed task
    completed_task = Task(
        date="10.06.2025",
        day_of_week="Вторник",
        task="Completed Task",
        status=TaskStatus.DONE,  # This is the key - task is DONE
        goal_id=1,
        goal_name="Test Goal",
    )
    storage.tasks = [completed_task]

    # Mock is_subscribed and format_date
    with patch("scheduler.tasks.is_subscribed", return_value=True):
        monkeypatch.setattr("scheduler.tasks.format_date", lambda x: "10.06.2025")

        await sched._send_today_tasks(bot, user_id)

    # Should send congratulations message for completed tasks
    assert len(bot.sent) == 1
    assert "Все задачи на сегодня уже выполнены" in bot.sent[0]["text"]
    assert "Отличная работа" in bot.sent[0]["text"]


@pytest.mark.asyncio
async def test_send_today_tasks_multiple_incomplete_tasks(
    enhanced_scheduler, monkeypatch
):
    """Test _send_today_tasks with multiple incomplete tasks (covers line 188-197)."""
    sched, storage, _ = enhanced_scheduler
    bot = MockBot()
    user_id = 888

    # Create multiple incomplete tasks
    task1 = Task(
        date="10.06.2025",
        day_of_week="Вторник",
        task="First Task",
        status=TaskStatus.NOT_DONE,
        goal_id=1,
        goal_name="Goal One",
    )
    task2 = Task(
        date="10.06.2025",
        day_of_week="Вторник",
        task="Second Task",
        status=TaskStatus.PARTIALLY_DONE,
        goal_id=2,
        goal_name="Goal Two",
    )
    storage.tasks = [task1, task2]

    # Mock is_subscribed and format_date
    with patch("scheduler.tasks.is_subscribed", return_value=True):
        monkeypatch.setattr("scheduler.tasks.format_date", lambda x: "10.06.2025")

        await sched._send_today_tasks(bot, user_id)

    # Should send multiple tasks in list format
    assert len(bot.sent) == 1
    message_text = bot.sent[0]["text"]
    assert "Доброе утро! Ваши задачи на сегодня:" in message_text
    assert "Goal One" in message_text
    assert "Goal Two" in message_text
    assert "First Task" in message_text
    assert "Second Task" in message_text


@pytest.mark.asyncio
async def test_send_today_tasks_exception_handling(enhanced_scheduler, monkeypatch):
    """Test _send_today_tasks exception handling (covers line 201-202)."""
    sched, storage, _ = enhanced_scheduler
    bot = MockBot()
    user_id = 777

    # Make storage raise an exception
    storage.should_raise = True

    # Mock is_subscribed and format_date
    with patch("scheduler.tasks.is_subscribed", return_value=True):
        monkeypatch.setattr("scheduler.tasks.format_date", lambda x: "10.06.2025")

        # Should not raise exception, should be logged instead
        await sched._send_today_tasks(bot, user_id)

    # No messages should be sent due to exception
    assert len(bot.sent) == 0


@pytest.mark.asyncio
async def test_send_evening_reminder_all_completed(enhanced_scheduler, monkeypatch):
    """Test _send_evening_reminder when all tasks completed (covers line 225)."""
    sched, storage, _ = enhanced_scheduler
    bot = MockBot()
    user_id = 666

    # Create only completed tasks
    completed_task = Task(
        date="10.06.2025",
        day_of_week="Вторник",
        task="Completed Evening Task",
        status=TaskStatus.DONE,
        goal_id=1,
        goal_name="Evening Goal",
    )
    storage.tasks = [completed_task]

    # Mock is_subscribed and format_date
    with patch("scheduler.tasks.is_subscribed", return_value=True):
        monkeypatch.setattr("scheduler.tasks.format_date", lambda x: "10.06.2025")

        await sched._send_evening_reminder(bot, user_id)

    # Should send congratulations instead of reminder
    assert len(bot.sent) == 1
    assert "Поздравляем! Вы выполнили все задачи на сегодня" in bot.sent[0]["text"]


@pytest.mark.asyncio
async def test_send_evening_reminder_exception_handling(
    enhanced_scheduler, monkeypatch
):
    """Test _send_evening_reminder exception handling (covers line 234-235)."""
    sched, storage, _ = enhanced_scheduler
    bot = MockBot()
    user_id = 555

    # Make storage raise an exception
    storage.should_raise = True

    # Mock is_subscribed and format_date
    with patch("scheduler.tasks.is_subscribed", return_value=True):
        monkeypatch.setattr("scheduler.tasks.format_date", lambda x: "10.06.2025")

        # Should not raise exception, should be logged instead
        await sched._send_evening_reminder(bot, user_id)

    # No messages should be sent due to exception
    assert len(bot.sent) == 0


@pytest.mark.asyncio
async def test_send_motivation_no_active_goals(enhanced_scheduler):
    """Test _send_motivation when user has no active goals (covers line 249)."""
    sched, storage, llm = enhanced_scheduler
    bot = MockBot()
    user_id = 444

    # No active goals
    storage.goals = []

    # Mock is_subscribed
    with patch("scheduler.tasks.is_subscribed", return_value=True):
        await sched._send_motivation(bot, user_id)

    # Should return early, no motivation sent
    assert len(bot.sent) == 0
    assert "generate_motivation" not in llm.called


@pytest.mark.asyncio
async def test_send_motivation_exception_handling(enhanced_scheduler):
    """Test _send_motivation exception handling (covers line 274-275)."""
    sched, storage, llm = enhanced_scheduler
    bot = MockBot()
    user_id = 333

    # Add a goal but make storage raise exception
    test_goal = Goal(
        goal_id=1,
        name="Test Goal",
        description="Test Description",
        deadline="01.07.2025",
        daily_time="1 час",
        start_date="01.06.2025",
        status=GoalStatus.ACTIVE,
        priority=GoalPriority.HIGH,
        tags=["test"],
    )
    storage.goals = [test_goal]
    storage.should_raise = True

    # Mock is_subscribed
    with patch("scheduler.tasks.is_subscribed", return_value=True):
        # Should not raise exception, should be logged instead
        await sched._send_motivation(bot, user_id)

    # No messages should be sent due to exception
    assert len(bot.sent) == 0


@pytest.mark.asyncio
async def test_send_today_tasks_unsubscribed_user(enhanced_scheduler, monkeypatch):
    """Test _send_today_tasks with unsubscribed user."""
    sched, storage, _ = enhanced_scheduler
    bot = MockBot()
    user_id = 222

    # Mock is_subscribed to return False
    with patch("scheduler.tasks.is_subscribed", return_value=False):
        await sched._send_today_tasks(bot, user_id)

    # Should return early, no messages sent
    assert len(bot.sent) == 0


@pytest.mark.asyncio
async def test_send_evening_reminder_unsubscribed_user(enhanced_scheduler):
    """Test _send_evening_reminder with unsubscribed user."""
    sched, storage, _ = enhanced_scheduler
    bot = MockBot()
    user_id = 111

    # Mock is_subscribed to return False
    with patch("scheduler.tasks.is_subscribed", return_value=False):
        await sched._send_evening_reminder(bot, user_id)

    # Should return early, no messages sent
    assert len(bot.sent) == 0


@pytest.mark.asyncio
async def test_send_motivation_unsubscribed_user(enhanced_scheduler):
    """Test _send_motivation with unsubscribed user."""
    sched, storage, _ = enhanced_scheduler
    bot = MockBot()
    user_id = 000

    # Mock is_subscribed to return False
    with patch("scheduler.tasks.is_subscribed", return_value=False):
        await sched._send_motivation(bot, user_id)

    # Should return early, no messages sent
    assert len(bot.sent) == 0


@pytest.mark.asyncio
async def test_scheduler_start_already_running():
    """Test scheduler start when already running."""
    storage = MockAsyncStorage()
    llm = MockAsyncLLM()

    # Create scheduler with current event loop
    scheduler = Scheduler(storage, llm, event_loop=asyncio.get_running_loop())

    # Start scheduler
    scheduler.start()
    assert scheduler.scheduler is not None
    assert scheduler.scheduler.running

    # Start again - should not create new scheduler
    old_scheduler = scheduler.scheduler
    scheduler.start()
    assert scheduler.scheduler is old_scheduler  # Same instance
