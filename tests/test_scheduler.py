from datetime import datetime

import pytest

from scheduler.tasks import Scheduler
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS


class DummyGoalManager:
    def __init__(self):
        self.called = {}

    # --- methods used by Scheduler ---
    async def get_today_task_async(self, user_id):  # noqa: D401
        self.called["get_today_task"] = user_id
        return {
            COL_DATE: "01.05.2025",
            COL_DAYOFWEEK: "Четверг",
            COL_TASK: "Task",
            COL_STATUS: "Не выполнено",
        }

    def generate_motivation_message(self, user_id):  # noqa: D401
        self.called["generate_motivation_message"] = user_id
        return "Keep going!"

    async def generate_motivation_message_async(self, user_id):  # noqa: D401
        self.called["generate_motivation_message"] = user_id
        return "Keep going!"


class DummyBot:
    def __init__(self):
        self.sent: list[dict] = []

    async def send_message(self, **kwargs):  # noqa: D401
        self.sent.append(kwargs)


@pytest.fixture()
def scheduler_instance():
    gm = DummyGoalManager()
    sched = Scheduler(gm)
    return sched, gm


def test_add_user_jobs(scheduler_instance):
    sched, _ = scheduler_instance
    bot = DummyBot()
    sched.add_user_jobs(bot, user_id=123)

    jobs = {j.id: j for j in sched.scheduler.get_jobs()}
    assert set(jobs) == {"morning_123", "evening_123", "motivation_123"}

    # Проверяем аргументы первой джобы
    job = jobs["morning_123"]
    assert job.args[1] == 123  # user_id


@pytest.mark.asyncio
async def test_send_today_task(scheduler_instance):
    sched, gm = scheduler_instance
    bot = DummyBot()

    await sched._send_today_task(bot, 555)

    # goal_manager вызван
    assert gm.called["get_today_task"] == 555
    # bot.send_message вызван с текстом задачи
    assert bot.sent
    assert "📅 Задача на сегодня" in bot.sent[0]["text"]


@pytest.mark.asyncio
async def test_send_motivation(scheduler_instance):
    sched, gm = scheduler_instance
    bot = DummyBot()

    await sched._send_motivation(bot, 777)

    assert gm.called["generate_motivation_message"] == 777
    assert bot.sent[0]["text"] == "Keep going!"
