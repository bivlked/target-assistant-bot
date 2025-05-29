"""Common handlers for the Telegram bot with multi-goal support."""

from __future__ import annotations

import sentry_sdk
import structlog
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.dependency_injection import get_async_storage
from scheduler.tasks import Scheduler
from utils.subscription import is_subscribed, subscribe_user
from core.metrics import USER_COMMANDS_TOTAL

logger = structlog.get_logger(__name__)

# Text constants
WELCOME_TEXT = (
    "🎯 Добро пожаловать в Target Assistant Bot!\n\n"
    "Я помогу вам:\n"
    "• 📝 Ставить и управлять целями\n"
    "• 📋 Создавать ежедневные планы\n"
    "• 📊 Отслеживать прогресс\n"
    "• 💪 Получать мотивацию\n\n"
    "Возможности:\n"
    "• Поддержка до 10 активных целей\n"
    "• Автоматическое планирование задач\n"
    "• Умная статистика и аналитика\n"
    "• Интеграция с Google Sheets\n\n"
    "Используйте /my_goals для начала работы с целями!"
)

HELP_TEXT = (
    "🤖 Помощь по Target Assistant Bot\n\n"
    "Основные команды:\n"
    "• /my_goals - управление целями\n"
    "• /add_goal - создать новую цель (через кнопки)\n"
    "• /setgoal - создать цель (через диалог)\n"
    "• /today - задачи на сегодня\n"
    "• /status - общий прогресс\n"
    "• /check - отметить выполнение\n"
    "• /motivation - получить мотивацию\n"
    "• /reset - сброс всех данных\n\n"
    "Возможности:\n"
    "• Создавайте до 10 активных целей\n"
    "• Устанавливайте приоритеты и теги\n"
    "• Отслеживайте прогресс в реальном времени\n"
    "• Получайте персонализированные планы\n\n"
    "Все данные синхронизируются с Google Sheets!"
)

CANCEL_TEXT = "❌ Операция отменена."

UNKNOWN_TEXT = (
    "🤔 Неизвестная команда.\n" "Используйте /help для списка доступных команд."
)

RESET_SUCCESS_TEXT = (
    "✅ Все ваши данные успешно удалены.\n"
    "Используйте /start для повторной настройки."
)


def start_handler(scheduler: Scheduler):
    """Factory to create the /start command handler with multi-goal support.

    The /start command subscribes the user and sets up their environment.

    Args:
        scheduler: Instance of Scheduler to add user-specific jobs.

    Returns:
        An asynchronous handler function for `CommandHandler`.
    """

    async def _handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        USER_COMMANDS_TOTAL.labels(command_name="/start").inc()
        user_id = update.effective_user.id
        sentry_sdk.set_tag("user_id", user_id)

        # Subscribe user
        subscribe_user(user_id)

        # Setup user spreadsheet
        storage = get_async_storage()
        await storage.create_spreadsheet(user_id)

        # Add scheduler jobs
        scheduler.add_user_jobs(context.bot, user_id)

        # Welcome message with inline buttons
        keyboard = [
            [InlineKeyboardButton("🎯 Мои цели", callback_data="back_to_goals")],
            [InlineKeyboardButton("➕ Создать цель", callback_data="add_goal")],
            [
                InlineKeyboardButton(
                    "📊 Открыть таблицу", callback_data="show_spreadsheet"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            WELCOME_TEXT,
            reply_markup=reply_markup,
        )

    return _handler


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /help command, sending a help message."""
    USER_COMMANDS_TOTAL.labels(command_name="/help").inc()
    user_id = update.effective_user.id
    sentry_sdk.set_tag("user_id", user_id)

    await update.message.reply_text(HELP_TEXT, disable_web_page_preview=True)


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /cancel command, typically used to exit conversations."""
    USER_COMMANDS_TOTAL.labels(command_name="/cancel").inc()
    user_id = update.effective_user.id
    sentry_sdk.set_tag("user_id", user_id)

    await update.message.reply_text(CANCEL_TEXT)


async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /reset command - deletes all user data."""
    USER_COMMANDS_TOTAL.labels(command_name="/reset").inc()
    user_id = update.effective_user.id
    sentry_sdk.set_tag("user_id", user_id)

    if not await is_subscribed(user_id):
        await update.message.reply_text(
            "❌ Вы не подписаны на бота. Используйте /start для начала."
        )
        return

    # Confirm deletion
    keyboard = [
        [
            InlineKeyboardButton("⚠️ Да, удалить все", callback_data="confirm_reset"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_reset"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚠️ ВНИМАНИЕ!\n\n"
        "Это действие удалит:\n"
        "• Все ваши цели\n"
        "• Все планы и задачи\n"
        "• Google Sheets таблицу\n"
        "• Весь прогресс\n\n"
        "Это действие нельзя отменить!\n\n"
        "Вы действительно хотите продолжить?",
        reply_markup=reply_markup,
    )


async def confirm_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and execute reset."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    storage = get_async_storage()

    try:
        # Delete spreadsheet
        await storage.delete_spreadsheet(user_id)

        await query.edit_message_text(
            RESET_SUCCESS_TEXT + "\n\n" "Используйте /start для повторной настройки."
        )

    except Exception as e:
        logger.error(f"Error resetting user data: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при удалении данных.\n"
            "Попробуйте позже или обратитесь в поддержку."
        )


async def cancel_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel reset operation."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("❌ Сброс данных отменен.")


async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles unknown commands."""
    USER_COMMANDS_TOTAL.labels(command_name="unknown").inc()
    user_id = update.effective_user.id
    sentry_sdk.set_tag("user_id", user_id)

    await update.message.reply_text(UNKNOWN_TEXT)
