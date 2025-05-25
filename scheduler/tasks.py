from __future__ import annotations

import logging
import sentry_sdk
import asyncio
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from config import scheduler_cfg
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS
from core.goal_manager import GoalManager

from texts import (
    EVENING_REMINDER_TEXT,  # Add new scheduler texts
    NO_TASKS_FOR_TODAY_SCHEDULER_TEXT,
    TODAY_TASK_DETAILS_TEMPLATE,  # Reuse from task_management
)

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

    def __init__(
        self,
        goal_manager: GoalManager,
        event_loop: asyncio.AbstractEventLoop | None = None,
    ):
        """Initializes the Scheduler with a GoalManager instance and sets up APScheduler.

        Args:
            goal_manager: GoalManager instance for accessing user data
            event_loop: Optional event loop to use. If None, will get the current running loop when needed.
        """
        self.goal_manager = goal_manager
        self._event_loop = event_loop
        self.scheduler = None  # Will be initialized in start()

    def start(self):
        """Starts the APScheduler if it's not already running."""
        if self.scheduler is None:
            # If no event loop was provided, try to get the current one
            if self._event_loop is None:
                try:
                    self._event_loop = asyncio.get_running_loop()
                except RuntimeError:
                    logger.error("No running event loop found. Scheduler not started.")
                    return

            # Create scheduler with the event loop
            self.scheduler = AsyncIOScheduler(
                timezone=scheduler_cfg.timezone,
                event_loop=self._event_loop,
            )

        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def add_user_jobs(self, bot: Bot, user_id: int):
        """Adds all standard periodic jobs for a given user.

        This includes:
        - Morning task reminder (_send_today_task).
        - Evening check-in reminder (_send_evening_reminder).
        - Periodic motivational message (_send_motivation).

        Existing jobs with the same ID for the user will be replaced.
        """
        if self.scheduler is None:
            logger.error("Scheduler not initialized. Cannot add user jobs.")
            return

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
