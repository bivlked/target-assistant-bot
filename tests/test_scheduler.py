from datetime import datetime

import pytest

from scheduler.tasks import Scheduler
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS


class DummyGoalManager:
    def __init__(self):
        self.called: dict[str, int] = {}

    # --- методы, используемые Scheduler ---
    def get_today_task(self, user_id):  # noqa: D401
        self.called["get_today_task"] = user_id
        return {
            COL_DATE: "01.05.2025",
            COL_DAYOFWEEK: "Четверг",
            COL_TASK: "Task",
            COL_STATUS: "Не выполнено",
        }

    async def get_today_task_async(self, user_id):  # noqa: D401
        # просто обёртка вокруг sync-метода
        return self.get_today_task(user_id)

    def generate_motivation_message(self, user_id):  # noqa: D401
        self.called["generate_motivation_message"] = user_id
        return "Keep going!"

    async def generate_motivation_message_async(self, user_id):  # noqa: D401
        # обёртка вокруг sync-метода
        return self.generate_motivation_message(user_id)


class DummyBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, **kwargs):
        self.sent.append(kwargs)


@pytest.fixture()
def scheduler_instance():
    gm = DummyGoalManager()
    return Scheduler(gm), gm


def test_add_user_jobs(scheduler_instance):
    sched, _ = scheduler_instance
    bot = DummyBot()
    sched.add_user_jobs(bot, 123)
    jobs = {j.id for j in sched.scheduler.get_jobs()}
    assert jobs == {"morning_123", "evening_123", "motivation_123"}


@pytest.mark.asyncio
async def test_send_today_task(scheduler_instance):
    sched, gm = scheduler_instance
    bot = DummyBot()
    await sched._send_today_task(bot, 555)
    assert gm.called["get_today_task"] == 555
    assert bot.sent and "📅 Задача на сегодня" in bot.sent[0]["text"]


@pytest.mark.asyncio
async def test_send_motivation(scheduler_instance):
    sched, gm = scheduler_instance
    bot = DummyBot()
    await sched._send_motivation(bot, 777)
    assert gm.called["generate_motivation_message"] == 777
    assert bot.sent[0]["text"] == "Keep going!"
