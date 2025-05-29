"""Handler for the /setgoal conversation flow with multi-goal support."""

from __future__ import annotations

import sentry_sdk
import structlog
from datetime import datetime, timezone
from typing import Final, cast, Any, Dict

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from core.dependency_injection import get_async_storage, get_async_llm
from core.models import Goal, GoalPriority, GoalStatus
from utils.helpers import format_date
from utils.period_parser import parse_period
from utils.subscription import is_subscribed
from core.metrics import USER_COMMANDS_TOTAL

logger = structlog.get_logger(__name__)

# ConversationHandler states
TEXT_GOAL: Final = 0
DEADLINE: Final = 1
AVAILABLE_TIME: Final = 2

# Text messages
PROMPT_GOAL_TEXT = (
    "🎯 *Создание новой цели*\n\n"
    "Опишите вашу цель подробно (минимум 10 символов).\n"
    "Например: 'Изучить Python и создать веб-приложение'"
)

PROMPT_DEADLINE_TEXT = (
    "📅 Укажите срок достижения цели.\n" "Например: '3 месяца', '6 недель', '90 дней'"
)

PROMPT_AVAILABLE_TIME_TEXT = (
    "⏰ Сколько времени в день вы готовы уделять этой цели?\n"
    "Например: '1 час', '30 минут', '2 часа'"
)

VALIDATE_GOAL_MIN_LENGTH_TEXT = (
    "❌ Описание цели слишком короткое. Минимум 10 символов."
)

VALIDATE_DEADLINE_RANGE_TEXT = (
    "❌ Неверный срок. Укажите от 1 до 120 дней.\n"
    "Например: '2 месяца', '8 недель', '60 дней'"
)

GENERATING_PLAN_TEXT = "⏳ Создаю цель и генерирую план достижения..."

SETGOAL_SUCCESS_TEXT_TEMPLATE = (
    "✅ Цель успешно создана!\n\n"
    "🎯 *Цель:* {goal_text}\n"
    "📊 План составлен на {total_days} дней.\n\n"
    "📋 [Открыть таблицу]({spreadsheet_url})\n\n"
    "Используйте /today чтобы увидеть задачи на сегодня."
)

SETGOAL_ERROR_TEXT = "❌ Произошла ошибка при создании цели. Попробуйте позже."

CONVERSATION_CANCELLED_TEXT = "❌ Создание цели отменено."


async def _ask_deadline(update: Update):
    """Sends a message asking the user for the goal deadline."""
    assert update.message is not None
    await update.message.reply_text(PROMPT_DEADLINE_TEXT)


async def _ask_available_time(update: Update):
    """Sends a message asking the user for their daily time commitment."""
    assert update.message is not None
    await update.message.reply_text(PROMPT_AVAILABLE_TIME_TEXT)


def build_setgoal_conv() -> ConversationHandler:
    """Builds the ConversationHandler for the /setgoal command flow."""

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        USER_COMMANDS_TOTAL.labels(command_name="/setgoal").inc()
        user_id = update.effective_user.id
        sentry_sdk.set_tag("user_id", user_id)

        if not await is_subscribed(user_id):
            await update.message.reply_text(
                "❌ Вы не подписаны на бота. Используйте /start для начала."
            )
            return ConversationHandler.END

        # Check goal limit
        storage = get_async_storage()
        active_count = await storage.get_active_goals_count(user_id)
        if active_count >= 10:
            await update.message.reply_text(
                "❌ Достигнут лимит активных целей (10).\n"
                "Завершите или архивируйте существующие цели перед добавлением новых.\n\n"
                "Используйте /my_goals для управления целями."
            )
            return ConversationHandler.END

        await update.message.reply_text(PROMPT_GOAL_TEXT, parse_mode="Markdown")
        return TEXT_GOAL

    async def input_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        sentry_sdk.set_tag("user_id", user_id)

        text_raw = update.message.text or ""
        text = text_raw.strip()
        if len(text) < 10:
            await update.message.reply_text(VALIDATE_GOAL_MIN_LENGTH_TEXT)
            return TEXT_GOAL

        data_dict = cast(Dict[str, Any], context.user_data)
        data_dict["goal_text"] = text
        await _ask_deadline(update)
        return DEADLINE

    async def input_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        sentry_sdk.set_tag("user_id", user_id)

        text_raw = update.message.text or ""
        text = text_raw.strip()

        # Try to parse the period and ensure it does not exceed 120 days
        try:
            days = parse_period(text)
            if days <= 0 or days > 120:
                raise ValueError("Invalid day range")
        except ValueError:
            await update.message.reply_text(VALIDATE_DEADLINE_RANGE_TEXT)
            return DEADLINE

        data_dict = cast(Dict[str, Any], context.user_data)
        data_dict["deadline"] = text
        await _ask_available_time(update)
        return AVAILABLE_TIME

    async def input_available_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        sentry_sdk.set_tag("user_id", user_id)

        text_raw = update.message.text or ""
        text = text_raw.strip()
        data_dict = cast(Dict[str, Any], context.user_data)
        data_dict["available_time"] = text

        await update.message.reply_text(GENERATING_PLAN_TEXT)

        goal_text = data_dict["goal_text"]
        deadline = data_dict["deadline"]
        available_time = data_dict["available_time"]

        try:
            storage = get_async_storage()
            llm = get_async_llm()

            # Get next goal ID
            goal_id = await storage.get_next_goal_id(user_id)

            # Create goal object
            goal = Goal(
                goal_id=goal_id,
                name=f"Цель {goal_id}",  # Default name, user can change later
                description=goal_text,
                deadline=deadline,
                daily_time=available_time,
                start_date=format_date(datetime.now(timezone.utc)),
                status=GoalStatus.ACTIVE,
                priority=GoalPriority.MEDIUM,
                tags=[],
                progress_percent=0,
            )

            # Save goal
            spreadsheet_url = await storage.save_goal_info(user_id, goal)

            # Generate plan
            plan = await llm.generate_plan(goal_text, deadline, available_time)

            # Save plan
            await storage.save_plan(user_id, goal_id, plan)

            # Calculate total days
            total_days = len(plan)

            await update.message.reply_text(
                SETGOAL_SUCCESS_TEXT_TEMPLATE.format(
                    goal_text=goal_text,
                    total_days=total_days,
                    spreadsheet_url=spreadsheet_url,
                ),
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )

        except Exception as e:
            logger.error(f"Error creating goal: {e}")
            await update.message.reply_text(SETGOAL_ERROR_TEXT)

        return ConversationHandler.END

    async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user:
            sentry_sdk.set_tag("user_id", update.effective_user.id)

        await update.message.reply_text(CONVERSATION_CANCELLED_TEXT)
        return ConversationHandler.END

    return ConversationHandler(
        entry_points=[CommandHandler("setgoal", start)],
        states={
            TEXT_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_goal)],
            DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_deadline)],
            AVAILABLE_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_available_time)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        block=True,
        name="setgoal_conv",
        persistent=False,
    )
