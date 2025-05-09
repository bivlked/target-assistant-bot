from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import CommandHandler, MessageHandler, filters

from core.goal_manager import GoalManager
from scheduler.tasks import Scheduler
from texts import WELCOME_TEXT, HELP_TEXT, CANCEL_TEXT, UNKNOWN_TEXT


def start_handler(goal_manager: GoalManager, scheduler: Scheduler):
    async def _handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        await goal_manager.setup_user_async(user_id)
        scheduler.add_user_jobs(context.bot, user_id)
        await update.message.reply_text(WELCOME_TEXT)

    return _handler


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        HELP_TEXT, parse_mode="Markdown", disable_web_page_preview=True
    )


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(CANCEL_TEXT)


def reset_handler(goal_manager: GoalManager):
    async def _handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await goal_manager.reset_user_async(update.effective_user.id)
        await update.message.reply_text(
            "🗑️ Все ваши данные удалены. Используйте /setgoal, чтобы начать заново."
        )

    return _handler


def unknown_handler():
    async def _handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(UNKNOWN_TEXT)

    return _handler
