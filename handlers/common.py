"""Common handlers for the Telegram bot, such as /start, /help, /reset, etc."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import CommandHandler, MessageHandler, filters

from core.goal_manager import GoalManager
from scheduler.tasks import Scheduler
from texts import WELCOME_TEXT, HELP_TEXT, CANCEL_TEXT, UNKNOWN_TEXT, RESET_SUCCESS_TEXT
from core.metrics import USER_COMMANDS_TOTAL


def start_handler(goal_manager: GoalManager, scheduler: Scheduler):
    """Factory to create the /start command handler.

    The /start command initializes user-specific data (spreadsheet) and schedules
    periodic jobs (like reminders) for the user.

    Args:
        goal_manager: Instance of GoalManager to handle goal setup.
        scheduler: Instance of Scheduler to add user-specific jobs.

    Returns:
        An asynchronous handler function for `CommandHandler`.
    """

    async def _handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        USER_COMMANDS_TOTAL.labels(command_name="/start").inc()
        # Telegram guarantees effective_user and message for /start command
        assert update.effective_user is not None  # runtime safety for mypy
        user_id = update.effective_user.id
        await goal_manager.setup_user(user_id)
        scheduler.add_user_jobs(context.bot, user_id)
        assert update.message is not None
        await update.message.reply_text(WELCOME_TEXT)

    return _handler


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /help command, sending a help message."""
    USER_COMMANDS_TOTAL.labels(command_name="/help").inc()
    assert update.message is not None
    await update.message.reply_text(
        HELP_TEXT, parse_mode="Markdown", disable_web_page_preview=True
    )


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /cancel command, typically used to exit conversations."""
    USER_COMMANDS_TOTAL.labels(command_name="/cancel").inc()
    assert update.message is not None
    await update.message.reply_text(CANCEL_TEXT)


def reset_handler(goal_manager: GoalManager):
    """Factory to create the /reset command handler.

    The /reset command deletes all user data, including their Google Spreadsheet.

    Args:
        goal_manager: Instance of GoalManager to handle data reset.

    Returns:
        An asynchronous handler function for `CommandHandler`.
    """

    async def _handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        USER_COMMANDS_TOTAL.labels(command_name="/reset").inc()
        assert update.effective_user is not None
        assert update.message is not None
        await goal_manager.reset_user(update.effective_user.id)
        await update.message.reply_text(RESET_SUCCESS_TEXT)

    return _handler


def unknown_handler():
    """Factory to create a handler for unknown commands.

    Responds to any command not explicitly handled by other handlers.

    Returns:
        An asynchronous handler function for `MessageHandler`.
    """

    async def _handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        USER_COMMANDS_TOTAL.labels(command_name="unknown").inc()
        assert update.message is not None
        await update.message.reply_text(UNKNOWN_TEXT)

    return _handler
