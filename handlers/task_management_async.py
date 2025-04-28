from __future__ import annotations

from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from core.goal_manager import GoalManager
from utils.helpers import format_date
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS


def build_async_handlers(goal_manager: GoalManager) -> CommandHandler:
    """Возвращает CommandHandler для команды /today_async.

    Использует AsyncSheetsManager внутри GoalManager.
    """

    async def today_async(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not getattr(goal_manager, "sheets_async", None):
            await update.message.reply_text("Асинхронный клиент ещё не настроен.")
            return

        user_id = update.effective_user.id
        date_str = format_date(datetime.now())
        task = await goal_manager.sheets_async.get_task_for_date(user_id, date_str)  # type: ignore[attr-defined]
        if task:
            text = (
                f"📅 Задача на сегодня ({task[COL_DATE]}, {task[COL_DAYOFWEEK]}):\n\n"
                f"📝 {task[COL_TASK]}\n\nСтатус: {task[COL_STATUS]}"
            )
        else:
            text = "Сначала установите цель с помощью /setgoal."
        await update.message.reply_text(text)

    return CommandHandler("today_async", today_async) 