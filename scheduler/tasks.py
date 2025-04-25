from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot

from config import scheduler_cfg
from utils.helpers import get_day_of_week

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, goal_manager):
        self.goal_manager = goal_manager
        self.scheduler = BackgroundScheduler(timezone=scheduler_cfg.timezone)

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
        )

        # Мотивационное сообщение
        self.scheduler.add_job(
            self._send_motivation,
            "interval",
            args=[bot, user_id],
            hours=scheduler_cfg.motivation_interval_hours,
            id=f"motivation_{user_id}",
            replace_existing=True,
        )

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()

    # -------------------------------------------------
    # Внутренние методы
    # -------------------------------------------------
    def _send_today_task(self, bot: Bot, user_id: int):
        try:
            task = self.goal_manager.get_today_task(user_id)
            if task:
                text = (
                    f"📅 Задача на сегодня ({task['Date']}, {task['DayOfWeek']}):\n\n"
                    f"📝 {task['Task']}\n\nСтатус: {task['Status']}"
                )
            else:
                text = "На сегодня задач нет. Установите новую цель командой /setgoal."
            bot.send_message(chat_id=user_id, text=text)
        except Exception as e:
            logger.error("Ошибка при отправке утренней задачи: %s", e)

    def _send_evening_reminder(self, bot: Bot, user_id: int):
        try:
            bot.send_message(chat_id=user_id, text="Не забудьте отметить прогресс командой /check! ✍️")
        except Exception as e:
            logger.error("Ошибка при отправке вечернего напоминания: %s", e)

    def _send_motivation(self, bot: Bot, user_id: int):
        try:
            msg = self.goal_manager.generate_motivation_message(user_id)
            bot.send_message(chat_id=user_id, text=msg)
        except Exception as e:
            logger.error("Ошибка при отправке мотивационного сообщения: %s", e) 