from __future__ import annotations

import logging
import sentry_sdk
import structlog
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from config import scheduler_cfg
from core.models import TaskStatus
from utils.helpers import format_date
from utils.subscription import is_subscribed
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)

# Text constants
EVENING_REMINDER_TEXT = (
    "🌙 Доброй ночи! Не забудьте отметить прогресс по сегодняшним задачам!\n"
    "Используйте /check для обновления статуса."
)

NO_TASKS_FOR_TODAY_SCHEDULER_TEXT = (
    "📅 На сегодня у вас нет запланированных задач.\n"
    "Отличный день для отдыха или планирования новых целей! 😊"
)

MORNING_TASK_TEMPLATE = (
    "☀️ Доброе утро! Ваши задачи на сегодня:\n\n"
    "{tasks_text}\n\n"
    "Желаю продуктивного дня! 💪"
)

SINGLE_TASK_TEMPLATE = (
    "📋 *{goal_name}*\n"
    "📝 {task_text}\n"
    "📅 {date} ({day_of_week})\n"
    "⏰ Статус: {status}"
)

MULTIPLE_TASKS_ITEM = "• *{goal_name}*: {task_text}"


class Scheduler:
    """Manages scheduled tasks for users with multi-goal support.

    Uses APScheduler with an AsyncIOScheduler to run jobs asynchronously.
    Works directly with storage and llm instances for multi-goal functionality.
    """

    def __init__(
        self,
        storage,
        llm,
        event_loop: asyncio.AbstractEventLoop | None = None,
    ):
        """Initializes the Scheduler with storage and llm instances.

        Args:
            storage: AsyncStorageInterface implementation
            llm: AsyncLLMInterface implementation
            event_loop: Optional event loop to use. If None, will get the current running loop when needed.
        """
        self.storage = storage
        self.llm = llm
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
        - Morning task reminder (_send_today_tasks).
        - Evening check-in reminder (_send_evening_reminder).
        - Periodic motivational message (_send_motivation).

        Existing jobs with the same ID for the user will be replaced.
        """
        if self.scheduler is None:
            logger.error("Scheduler not initialized. Cannot add user jobs.")
            return

        hour, minute = map(int, scheduler_cfg.morning_time.split(":"))
        self.scheduler.add_job(
            self._send_today_tasks,
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

    async def _send_today_tasks(self, bot: Bot, user_id: int):
        """(Job) Sends today's tasks to the user."""
        sentry_sdk.set_tag("user_id", user_id)
        sentry_sdk.set_tag("job_name", "_send_today_tasks")

        try:
            # Check if user is subscribed
            if not await is_subscribed(user_id):
                return

            today = format_date(datetime.now(timezone.utc))
            tasks = await self.storage.get_all_tasks_for_date(user_id, today)

            if not tasks:
                await bot.send_message(
                    chat_id=user_id, text=NO_TASKS_FOR_TODAY_SCHEDULER_TEXT
                )
                return

            # Filter incomplete tasks for morning reminder
            incomplete_tasks = [t for t in tasks if t.status != TaskStatus.DONE]

            if not incomplete_tasks:
                await bot.send_message(
                    chat_id=user_id,
                    text="✅ Все задачи на сегодня уже выполнены! Отличная работа! 🎉",
                )
                return

            if len(incomplete_tasks) == 1:
                # Single task - detailed view
                task = incomplete_tasks[0]
                goal_name = task.goal_name or f"Цель {task.goal_id}"
                status_text = {
                    TaskStatus.DONE: "✅ Выполнено",
                    TaskStatus.PARTIALLY_DONE: "🟡 Частично выполнено",
                    TaskStatus.NOT_DONE: "⬜ Не выполнено",
                }.get(task.status, "⬜ Не выполнено")

                text = SINGLE_TASK_TEMPLATE.format(
                    goal_name=goal_name,
                    task_text=task.task,
                    date=task.date,
                    day_of_week=task.day_of_week,
                    status=status_text,
                )
            else:
                # Multiple tasks - list view
                tasks_list = []
                for task in incomplete_tasks:
                    goal_name = task.goal_name or f"Цель {task.goal_id}"
                    tasks_list.append(
                        MULTIPLE_TASKS_ITEM.format(
                            goal_name=goal_name, task_text=task.task
                        )
                    )

                text = MORNING_TASK_TEMPLATE.format(tasks_text="\n".join(tasks_list))

            await bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")

        except Exception as e:
            logger.error(
                f"Error sending morning tasks for user {user_id}: {e}", exc_info=True
            )

    async def _send_evening_reminder(self, bot: Bot, user_id: int):
        """(Job) Sends an evening reminder to check off the daily tasks."""
        sentry_sdk.set_tag("user_id", user_id)
        sentry_sdk.set_tag("job_name", "_send_evening_reminder")

        try:
            # Check if user is subscribed
            if not await is_subscribed(user_id):
                return

            # Check if there are any incomplete tasks
            today = format_date(datetime.now(timezone.utc))
            tasks = await self.storage.get_all_tasks_for_date(user_id, today)
            incomplete_tasks = [t for t in tasks if t.status != TaskStatus.DONE]

            if not incomplete_tasks:
                # All tasks completed, send congratulations
                await bot.send_message(
                    chat_id=user_id,
                    text="🌟 Поздравляем! Вы выполнили все задачи на сегодня!\n"
                    "Отличная работа! 🎉",
                )
            else:
                # Send reminder
                await bot.send_message(chat_id=user_id, text=EVENING_REMINDER_TEXT)

        except Exception as e:
            logger.error(
                f"Error sending evening reminder for user {user_id}: {e}", exc_info=True
            )

    async def _send_motivation(self, bot: Bot, user_id: int):
        """(Job) Sends a motivational message to the user."""
        sentry_sdk.set_tag("user_id", user_id)
        sentry_sdk.set_tag("job_name", "_send_motivation")

        try:
            # Check if user is subscribed
            if not await is_subscribed(user_id):
                return

            # Get active goals and their progress
            goals = await self.storage.get_active_goals(user_id)
            if not goals:
                return  # No active goals, skip motivation

            # Build context about goals and progress
            goal_info = "Мои цели:\n"
            progress_summary = "Прогресс:\n"

            for goal in goals:
                stats = await self.storage.get_goal_statistics(user_id, goal.goal_id)
                goal_info += f"- {goal.name}: {goal.description}\n"
                progress_summary += f"- {goal.name}: {stats.progress_percent}% ({stats.completed_tasks}/{stats.total_tasks} задач)\n"

            # Generate motivation
            motivation = await self.llm.generate_motivation(goal_info, progress_summary)

            await bot.send_message(
                chat_id=user_id,
                text=f"💪 *Мотивация для вас:*\n\n{motivation}",
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.error(
                f"Error sending motivation message for user {user_id}: {e}",
                exc_info=True,
            )
