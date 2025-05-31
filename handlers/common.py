"""Common handlers for the Telegram bot with multi-goal support."""

from __future__ import annotations

import sentry_sdk
import structlog
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

from core.dependency_injection import get_async_storage
from scheduler.tasks import Scheduler
from utils.subscription import is_subscribed, subscribe_user
from core.metrics import USER_COMMANDS_TOTAL
from utils.helpers import escape_markdown_v2

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


def start_handler(scheduler: Scheduler) -> CommandHandler:
    """Create start command handler with scheduler dependency."""

    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - welcome user and setup."""
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        logger.info("User started bot", user_id=user_id)

        # Subscribe user and create spreadsheet
        subscribe_user(user_id)
        storage = get_async_storage()
        await storage.create_spreadsheet(user_id)

        # Add scheduled jobs for this user
        scheduler.add_user_jobs(context.bot, user_id)

        # Send welcome message with inline keyboard
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
            escape_markdown_v2(WELCOME_TEXT),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup,
        )

    return CommandHandler("start", start_command)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    logger.info("User requested help", user_id=user_id)

    await update.message.reply_text(
        escape_markdown_v2(HELP_TEXT),
        parse_mode="MarkdownV2",
        disable_web_page_preview=True,
    )


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    logger.info("User cancelled operation", user_id=user_id)

    await update.message.reply_text(
        escape_markdown_v2(CANCEL_TEXT), parse_mode="MarkdownV2"
    )


async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reset command - show confirmation dialog."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    if not await is_subscribed(user_id):
        await update.message.reply_text(
            escape_markdown_v2(
                "❌ Вы не подписаны на бота. Используйте /start для начала."
            ),
            parse_mode="MarkdownV2",
        )
        return

    # Create inline keyboard for confirmation
    keyboard = [
        [
            InlineKeyboardButton("⚠️ Да, удалить все", callback_data="confirm_reset"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_reset"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        escape_markdown_v2(
            "⚠️ *ВНИМАНИЕ!*\n\n"
            "Вы собираетесь удалить *все* ваши цели и данные.\n"
            "Это действие *нельзя отменить*!\n\n"
            "Вы уверены?"
        ),
        parse_mode="MarkdownV2",
        reply_markup=reply_markup,
    )


async def confirm_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle reset confirmation."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    await query.answer()

    user_id = query.from_user.id
    logger.info("User confirmed reset", user_id=user_id)

    try:
        storage = get_async_storage()
        await storage.delete_spreadsheet(user_id)

        await query.edit_message_text(
            escape_markdown_v2(RESET_SUCCESS_TEXT),
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        logger.error("Error during reset", user_id=user_id, error=str(e))
        await query.edit_message_text(
            escape_markdown_v2(
                "❌ Произошла ошибка при сбросе данных. Попробуйте позже."
            ),
            parse_mode="MarkdownV2",
        )


async def cancel_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle reset cancellation."""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    await query.edit_message_text(
        escape_markdown_v2("❌ Сброс данных отменен."), parse_mode="MarkdownV2"
    )


async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    logger.info("User sent unknown command", user_id=user_id)

    await update.message.reply_text(
        escape_markdown_v2(UNKNOWN_TEXT), parse_mode="MarkdownV2"
    )
