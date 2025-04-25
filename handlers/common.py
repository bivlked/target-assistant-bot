from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import CommandHandler, MessageHandler, filters

from core.goal_manager import GoalManager
from scheduler.tasks import Scheduler

WELCOME_TEXT = (
    "Привет! Я бот-помощник для достижения целей. Используйте /setgoal чтобы начать."
)
HELP_TEXT = (
    "/start - начать работу\n"
    "/setgoal - установить новую цель\n"
    "/today - задача на сегодня\n"
    "/check - отметить выполнение\n"
    "/status - статус цели\n"
    "/motivation - мотивационное сообщение\n"
    "/cancel - отменить текущую операцию\n"
    "/reset - удалить данные и начать заново"
)


def start_handler(goal_manager: GoalManager, scheduler: Scheduler):
    async def _handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        goal_manager.setup_user(user_id)
        scheduler.add_user_jobs(context.bot, user_id)
        await update.message.reply_text(WELCOME_TEXT)

    return _handler


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")


def reset_handler(goal_manager: GoalManager):
    async def _handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        goal_manager.reset_user(update.effective_user.id)
        await update.message.reply_text("Все ваши данные удалены. Используйте /setgoal, чтобы начать заново.")

    return _handler


def unknown_handler():
    async def _handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Я ещё не знаю такую команду, но учусь каждый день 🚀")

    return _handler 