from __future__ import annotations

import logging
import sentry_sdk
from datetime import datetime, time as dt_time, timezone
import asyncio
from typing import TYPE_CHECKING, cast, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from config import scheduler_cfg
from utils.helpers import get_day_of_week
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS
from core.goal_manager import GoalManager

from texts import (
    MORNING_REMINDER_TEXT,
    EVENING_REMINDER_TEXT,  # Add new scheduler texts
    NO_TASKS_FOR_TODAY_SCHEDULER_TEXT,
    TODAY_TASK_DETAILS_TEMPLATE,  # Reuse from task_management
)
from core.metrics import SCHEDULED_JOBS_EXECUTED_TOTAL

logger = logging.getLogger(__name__)

# Temporary reminder texts, to be moved to texts.py later # This section can be removed
# TEMP_MORNING_REMINDER_TEXT = (
# "☀️ Доброе утро! Время взяться за сегодняшнюю задачу для вашей цели!"
# )
# TEMP_EVENING_REMINDER_TEXT = (
# "🌙 Не забудьте отметить прогресс по сегодняшней задаче! /check"
# )


class Scheduler:
    """Manages scheduled tasks for users, like daily reminders and motivational messages.

    Uses APScheduler with an AsyncIOScheduler to run jobs asynchronously.
    Relies on GoalManager to fetch user-specific information for tasks.
    """

    def __init__(self, goal_manager):
        """Initializes the Scheduler with a GoalManager instance and sets up APScheduler."""
        self.goal_manager = goal_manager
        # AsyncIOScheduler по умолчанию будет использовать asyncio.get_event_loop().
        # Если он создается до того, как PTB Application запустит свой цикл,
        # и в основном потоке еще нет активного цикла, он может создать новый.
        # Важно, чтобы Application и AsyncIOScheduler использовали один и тот же цикл.
        # PTB Application создает и управляет своим циклом при run_polling().
        # Для совместимости, лучше инициализировать AsyncIOScheduler без явного event_loop,
        # и запускать scheduler.start() уже после того, как приложение настроено,
        # но до run_polling(), чтобы он подхватил цикл PTB или работал в контексте,
        # где asyncio.get_event_loop() вернет тот же цикл, что использует PTB.
        # Текущее место вызова в main.py (до run_polling) должно быть нормальным.
        self.scheduler = AsyncIOScheduler(timezone=scheduler_cfg.timezone)
        # Убрали явное управление event_loop здесь.
        # AsyncIOScheduler должен сам использовать существующий цикл или создать дефолтный,
        # который, надеемся, будет тем же, что и у PTB, если scheduler.start() вызывается правильно.

    def add_user_jobs(self, bot: Bot, user_id: int):
        """Adds all standard periodic jobs for a given user.

        This includes:
        - Morning task reminder (_send_today_task).
        - Evening check-in reminder (_send_evening_reminder).
        - Periodic motivational message (_send_motivation).

        Existing jobs with the same ID for the user will be replaced.
        """
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
        """Starts the APScheduler if it's not already running."""
        if not self.scheduler.running:
            self.scheduler.start()

    async def _send_today_task(self, bot: Bot, user_id: int):
        """(Job) Sends the daily task to the user if it's not completed."""
        sentry_sdk.set_tag("user_id", user_id)
        sentry_sdk.set_tag("job_name", "_send_today_task")
        try:
            task = await self.goal_manager.get_today_task(user_id)
            if task:
                text = TODAY_TASK_DETAILS_TEMPLATE.format(
                    date=task[COL_DATE],
                    day_of_week=task[COL_DAYOFWEEK],
                    task=task[COL_TASK],
                    status=task[COL_STATUS],
                )
            else:
                text = NO_TASKS_FOR_TODAY_SCHEDULER_TEXT
            await bot.send_message(chat_id=user_id, text=text)
        except Exception as e:
            logger.error(
                f"Error sending morning task for user {user_id}: {e}", exc_info=True
            )

    async def _send_evening_reminder(self, bot: Bot, user_id: int):
        """(Job) Sends an evening reminder to check off the daily task."""
        sentry_sdk.set_tag("user_id", user_id)
        sentry_sdk.set_tag("job_name", "_send_evening_reminder")
        try:
            await bot.send_message(
                chat_id=user_id,
                text=EVENING_REMINDER_TEXT,  # Use new constant
            )
        except Exception as e:
            logger.error(
                f"Error sending evening reminder for user {user_id}: {e}", exc_info=True
            )

    async def _send_motivation(self, bot: Bot, user_id: int):
        """(Job) Sends a motivational message to the user."""
        sentry_sdk.set_tag("user_id", user_id)
        sentry_sdk.set_tag("job_name", "_send_motivation")
        try:
            msg = await self.goal_manager.generate_motivation_message(user_id)
            await bot.send_message(chat_id=user_id, text=msg)
        except Exception as e:
            logger.error(
                f"Error sending motivation message for user {user_id}: {e}",
                exc_info=True,
            )

    # Method _send_daily_task_job and related TODOs for JobQueue have been removed
    # as the project uses APScheduler for scheduled tasks.

    # Removed TODOs related to JobQueue based evening/motivation reminders
    # Current APScheduler implementation already covers these functionalities.
