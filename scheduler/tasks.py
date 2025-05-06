from __future__ import annotations

import logging
from datetime import datetime
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from config import scheduler_cfg
from utils.helpers import get_day_of_week
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, goal_manager):
        self.goal_manager = goal_manager
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self.scheduler = AsyncIOScheduler(
            timezone=scheduler_cfg.timezone,
            event_loop=loop,
        )
    def add_user_jobs(self, bot: Bot, user_id: int):
        # Утреннее напоминание с задачей
        hour, minute = map(int, scheduler_cfg.morning_time.split(":"))
        self.scheduler.add_job(
            self._send_today_task,
            "cron",
            args=[bot, user_id],
            hour=hour,
            minute=minute,
            id=f"morning_{user_id}",
            replace_existing=True,
            coalesce=True,
        )

        # Вечернее напоминание о чек-ин
        hour, minute = map(int, scheduler_cfg.evening_time.split(":"))
        self.scheduler.add_job(
            self._send_evening_reminder,
            "cron",
            args=[bot, user_id],
            hour=hour,
            minute=minute,
            id=f"evening_{user_id}",
            replace_existing=True,
            coalesce=True,
        )

        # Мотивационное сообщение
        self.scheduler.add_job(
            self._send_motivation,
            "interval",
            args=[bot, user_id],
            hours=scheduler_cfg.motivation_interval_hours,
            id=f"motivation_{user_id}",
            replace_existing=True,
            coalesce=True,
        )

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()

    # -------------------------------------------------
    # Внутренние методы
    # -------------------------------------------------
    async def _send_today_task(self, bot: Bot, user_id: int):
        try:
            # Поддержка как нового async-API, так и старого sync (для тестовых заглушек)
            if hasattr(self.goal_manager, "get_today_task_async"):
                task = await self.goal_manager.get_today_task_async(user_id)  # type: ignore[attr-defined]
            else:
                task = self.goal_manager.get_today_task(user_id)  # type: ignore[attr-defined]
            if task:
                text = (
                    f"📅 Задача на сегодня ({task[COL_DATE]}, {task[COL_DAYOFWEEK]}):\n\n"
                    f"📝 {task[COL_TASK]}\n\nСтатус: {task[COL_STATUS]}"
                )
            else:
                text = "На сегодня задач нет. Установите новую цель командой /setgoal."
            await bot.send_message(chat_id=user_id, text=text)
        except Exception as e:
            logger.error("Ошибка при отправке утренней задачи: %s", e)

    async def _send_evening_reminder(self, bot: Bot, user_id: int):
        try:
            await bot.send_message(
                chat_id=user_id, text="Не забудьте отметить прогресс командой /check! ✍️"
            )
        except Exception as e:
            logger.error("Ошибка при отправке вечернего напоминания: %s", e)

    async def _send_motivation(self, bot: Bot, user_id: int):
        try:
            # Поддержка как нового async-API, так и старого sync (для тестовых заглушек)
            if hasattr(self.goal_manager, "generate_motivation_message_async"):
                msg = await self.goal_manager.generate_motivation_message_async(user_id)  # type: ignore[attr-defined]
            else:
                msg = self.goal_manager.generate_motivation_message(user_id)  # type: ignore[attr-defined]
            await bot.send_message(chat_id=user_id, text=msg)
        except Exception as e:
            logger.error("Ошибка при отправке мотивационного сообщения: %s", e)
