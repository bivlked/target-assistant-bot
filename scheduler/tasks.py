from __future__ import annotations

import logging
from datetime import datetime, time as dt_time, timezone
import asyncio
from typing import TYPE_CHECKING, cast, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from config import scheduler_cfg
from utils.helpers import get_day_of_week
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS
from core.goal_manager import GoalManager, STATUS_NOT_DONE

# from texts import MORNING_REMINDER_TEXT, EVENING_REMINDER_TEXT # These were missing and are now replaced by TEMP_*
from telegram.ext import JobQueue, ContextTypes, Application
from core.metrics import SCHEDULED_JOBS_EXECUTED_TOTAL

logger = logging.getLogger(__name__)

# Temporary reminder texts, to be moved to texts.py later
TEMP_MORNING_REMINDER_TEXT = (
    "☀️ Доброе утро! Время взяться за сегодняшнюю задачу для вашей цели!"
)
TEMP_EVENING_REMINDER_TEXT = (
    "🌙 Не забудьте отметить прогресс по сегодняшней задаче! /check"
)


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

    async def _send_today_task(self, bot: Bot, user_id: int):
        """Отправляет задачу на сегодня (если есть)."""
        try:
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
                chat_id=user_id,
                text="Не забудьте отметить прогресс командой /check! ✍️",
            )
        except Exception as e:
            logger.error("Ошибка при отправке вечернего напоминания: %s", e)

    async def _send_motivation(self, bot: Bot, user_id: int):
        """Отправляет мотивационное сообщение."""
        try:
            if hasattr(self.goal_manager, "generate_motivation_message_async"):
                msg = await self.goal_manager.generate_motivation_message_async(user_id)  # type: ignore[attr-defined]
            else:
                msg = self.goal_manager.generate_motivation_message(user_id)  # type: ignore[attr-defined]
            await bot.send_message(chat_id=user_id, text=msg)
        except Exception as e:
            logger.error("Ошибка при отправке мотивационного сообщения: %s", e)

    async def _send_daily_task_job(self, context: ContextTypes.DEFAULT_TYPE):
        """Job: отправляет ежедневную задачу и напоминание."""
        if context.job is None:
            logger.error("Scheduled job executed without context.job object.")
            SCHEDULED_JOBS_EXECUTED_TOTAL.labels(
                job_name="daily_task_reminder", status="error_no_job_context"
            ).inc()
            return

        job_context = cast(Dict[str, Any], context.job.data)
        user_id = job_context.get("user_id")
        bot = job_context.get("bot")

        if user_id is None or bot is None:
            logger.error(
                f"Scheduled job for user {user_id} missing user_id or bot in job_context."
            )
            SCHEDULED_JOBS_EXECUTED_TOTAL.labels(
                job_name="daily_task_reminder", status="error_missing_job_data"
            ).inc()
            return

        job_name = "daily_task_reminder"  # Consistent job name for metrics

        try:
            task_info = await self.goal_manager.get_today_task_async(user_id)
            if task_info and task_info.get("Статус") == STATUS_NOT_DONE:
                await bot.send_message(
                    user_id, TEMP_MORNING_REMINDER_TEXT
                )  # Use temporary text
                await bot.send_message(
                    user_id, f"📝 Ваша задача: {task_info['Задача']}"
                )
                SCHEDULED_JOBS_EXECUTED_TOTAL.labels(
                    job_name=job_name, status="success_sent"
                ).inc()
            else:
                SCHEDULED_JOBS_EXECUTED_TOTAL.labels(
                    job_name=job_name, status="success_not_sent"
                ).inc()
                logger.info(
                    f"Задача для user {user_id} на сегодня не найдена или уже выполнена."
                )
        except Exception as e:
            SCHEDULED_JOBS_EXECUTED_TOTAL.labels(
                job_name=job_name, status="error"
            ).inc()
            logger.error(
                f"Ошибка при отправке ежедневной задачи для user {user_id}: {e}",
                exc_info=True,
            )

    # --- Evening Reminder --- TODO: Add evening reminder for pending tasks

    # TODO: Implement evening reminder job and its metrics if needed.

    # TODO: Add job for sending motivation message periodically
