from datetime import datetime

import pytest

from scheduler.tasks import Scheduler
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS
from core.goal_manager import USER_FACING_STATUS_NOT_DONE


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


def test_add_user_jobs(scheduler_instance):
    """Tests that user-specific jobs are correctly added to APScheduler."""
    sched, _ = scheduler_instance
    bot = DummyBot()
    sched.add_user_jobs(bot, 123)
    jobs = {j.id for j in sched.scheduler.get_jobs()}
    assert jobs == {"morning_123", "evening_123", "motivation_123"}


@pytest.mark.asyncio
async def test_send_today_task(scheduler_instance):
    """Tests the _send_today_task job logic."""
    sched, gm = scheduler_instance
    bot = DummyBot()
    await sched._send_today_task(bot, 555)
    assert gm.called["get_today_task"] == 555
    assert bot.sent and "📅 Задача на сегодня" in bot.sent[0]["text"]


@pytest.mark.asyncio
async def test_send_motivation(scheduler_instance):
    """Tests the _send_motivation job logic."""
    sched, gm = scheduler_instance
    bot = DummyBot()
    await sched._send_motivation(bot, 777)
    assert gm.called["generate_motivation_message"] == 777
    assert bot.sent[0]["text"] == "Keep going! Mocked motivation!"
