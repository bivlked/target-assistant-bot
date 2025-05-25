"""Tests for the Scheduler and its job scheduling logic."""

import pytest
from unittest.mock import AsyncMock

from scheduler.tasks import Scheduler
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS
from core.goal_manager import USER_FACING_STATUS_NOT_DONE
from texts import (
    TODAY_TASK_DETAILS_TEMPLATE,
    NO_TASKS_FOR_TODAY_SCHEDULER_TEXT,
    EVENING_REMINDER_TEXT,
)


class DummyGoalManager:
    """A mock GoalManager for testing the Scheduler."""

    def __init__(self):
        """Initializes the mock, tracking called methods."""
        self.called: dict[str, int] = {}

    # --- methods used by Scheduler (now must be async) ---
    async def get_today_task(self, user_id: int) -> dict | None:
        """Simulates fetching today's task."""
        self.called["get_today_task"] = user_id
        # Simulate a case where a task is found
        return {
            COL_DATE: "01.05.2025",
            COL_DAYOFWEEK: "Четверг",
            COL_TASK: "Test Task from DummyGoalManager",
            COL_STATUS: USER_FACING_STATUS_NOT_DONE,
        }

    async def generate_motivation_message(self, user_id: int) -> str:
        """Simulates generating a motivational message."""
        self.called["generate_motivation_message"] = user_id
        return "Keep going! Mocked motivation!"


class DummyBot:
    """A mock Telegram Bot for testing message sending."""

    def __init__(self):
        """Initializes the mock, tracking sent messages."""
        self.sent = []

    async def send_message(self, **kwargs):
        """Simulates sending a message."""
        self.sent.append(kwargs)


@pytest.fixture()
def scheduler_instance():
    """Provides a Scheduler instance with a DummyGoalManager for tests."""
    gm = DummyGoalManager()
    return Scheduler(gm), gm


@pytest.mark.asyncio
async def test_add_user_jobs(scheduler_instance):
    """Tests that user-specific jobs are correctly added to APScheduler."""
    import asyncio

    sched, _ = scheduler_instance

    # Initialize scheduler with current event loop by calling start()
    sched._event_loop = asyncio.get_running_loop()
    sched.start()

    bot = DummyBot()
    sched.add_user_jobs(bot, 123)
    jobs = {j.id for j in sched.scheduler.get_jobs()}
    assert jobs == {"morning_123", "evening_123", "motivation_123"}


@pytest.mark.asyncio
async def test_send_today_task_task_exists(scheduler_instance, monkeypatch):
    """Tests the _send_today_task job logic when a task for today exists."""
    sched, gm = scheduler_instance
    bot = DummyBot()
    user_id = 555

    # Настраиваем мок gm.get_today_task
    today_date_str = "15.05.2025"
    today_day_of_week = "Четверг"
    task_text = "Scheduled Test Task"
    task_status = USER_FACING_STATUS_NOT_DONE
    gm.get_today_task = AsyncMock(
        return_value={
            COL_DATE: today_date_str,
            COL_DAYOFWEEK: today_day_of_week,
            COL_TASK: task_text,
            COL_STATUS: task_status,
        }
    )
    # Патчим format_date и get_day_of_week, используемые внутри _send_today_task, если они там есть
    # (В _send_today_task они не используются, он берет данные из get_today_task)

    await sched._send_today_task(bot, user_id)

    gm.get_today_task.assert_awaited_once_with(user_id)
    assert len(bot.sent) == 1
    expected_text = TODAY_TASK_DETAILS_TEMPLATE.format(
        date=today_date_str,
        day_of_week=today_day_of_week,
        task=task_text,
        status=task_status,
    )
    assert bot.sent[0]["text"] == expected_text
    assert bot.sent[0]["chat_id"] == user_id


@pytest.mark.asyncio
async def test_send_today_task_no_task(scheduler_instance):
    """Tests the _send_today_task job logic when no task for today exists."""
    sched, gm = scheduler_instance
    bot = DummyBot()
    user_id = 556

    gm.get_today_task = AsyncMock(return_value=None)  # Задачи нет

    await sched._send_today_task(bot, user_id)

    gm.get_today_task.assert_awaited_once_with(user_id)
    assert len(bot.sent) == 1
    assert bot.sent[0]["text"] == NO_TASKS_FOR_TODAY_SCHEDULER_TEXT
    assert bot.sent[0]["chat_id"] == user_id


@pytest.mark.asyncio
async def test_send_evening_reminder(scheduler_instance):
    """Tests the _send_evening_reminder job logic."""
    sched, gm = (
        scheduler_instance  # gm здесь не используется, но фикстура его возвращает
    )
    bot = DummyBot()
    user_id = 557

    await sched._send_evening_reminder(bot, user_id)

    assert len(bot.sent) == 1
    assert bot.sent[0]["text"] == EVENING_REMINDER_TEXT
    assert bot.sent[0]["chat_id"] == user_id


@pytest.mark.asyncio
async def test_send_motivation(scheduler_instance):
    """Tests the _send_motivation job logic."""
    sched, gm = scheduler_instance
    bot = DummyBot()
    await sched._send_motivation(bot, 777)
    assert gm.called["generate_motivation_message"] == 777
    assert bot.sent[0]["text"] == "Keep going! Mocked motivation!"
