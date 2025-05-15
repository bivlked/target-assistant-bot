"""Handler for the /setgoal conversation flow, allowing users to set new goals."""

from __future__ import annotations

import re
from datetime import timedelta, datetime
from typing import Final, cast, Any, Dict

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from core.goal_manager import GoalManager
from utils.period_parser import parse_period
from core.metrics import USER_COMMANDS_TOTAL
from texts import (
    PROMPT_DEADLINE_TEXT,
    PROMPT_AVAILABLE_TIME_TEXT,
    PROMPT_GOAL_TEXT,
    VALIDATE_GOAL_MIN_LENGTH_TEXT,
    VALIDATE_DEADLINE_RANGE_TEXT,
    GENERATING_PLAN_TEXT,
    SETGOAL_SUCCESS_TEXT_TEMPLATE,
    SETGOAL_ERROR_TEXT,
    CONVERSATION_CANCELLED_TEXT,
)

# ConversationHandler states
TEXT_GOAL: Final = 0
DEADLINE: Final = 1
AVAILABLE_TIME: Final = 2


# ------------------------------
# User input validation
# ------------------------------


async def _ask_deadline(update: Update):
    """Sends a message asking the user for the goal deadline."""
    assert update.message is not None
    await update.message.reply_text(PROMPT_DEADLINE_TEXT)


async def _ask_available_time(update: Update):
    """Sends a message asking the user for their daily time commitment."""
    assert update.message is not None
    await update.message.reply_text(PROMPT_AVAILABLE_TIME_TEXT)


# ------------------------------
# ConversationHandler construction function
# ------------------------------


def build_setgoal_conv(goal_manager: GoalManager) -> ConversationHandler:
    """Builds the ConversationHandler for the /setgoal command flow.

    Args:
        goal_manager: Instance of GoalManager to process the new goal.

    Returns:
        A ConversationHandler instance for PTB.
    """

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        USER_COMMANDS_TOTAL.labels(command_name="/setgoal").inc()
        assert update.message is not None
        await update.message.reply_text(PROMPT_GOAL_TEXT)
        return TEXT_GOAL

    async def input_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.message is not None
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
        assert update.message is not None
        text_raw = update.message.text or ""
        text = text_raw.strip()
        # Try to parse the period and ensure it does not exceed 90 days
        try:
            days = parse_period(text)
            if days > 90:
                raise ValueError
        except ValueError:
            await update.message.reply_text(VALIDATE_DEADLINE_RANGE_TEXT)
            return DEADLINE

        data_dict = cast(Dict[str, Any], context.user_data)
        data_dict["deadline"] = text
        await _ask_available_time(update)
        return AVAILABLE_TIME

    async def input_available_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.message is not None
        text_raw = update.message.text or ""
        text = text_raw.strip()
        data_dict = cast(Dict[str, Any], context.user_data)
        data_dict["available_time"] = text
        await update.message.reply_text(GENERATING_PLAN_TEXT)

        data_dict = cast(Dict[str, Any], context.user_data)
        goal_text = data_dict["goal_text"]
        deadline = data_dict["deadline"]
        available_time = data_dict["available_time"]
        assert update.effective_user is not None
        user_id = update.effective_user.id

        try:
            spreadsheet_url = await goal_manager.set_new_goal(
                user_id, goal_text, deadline, available_time
            )
            await update.message.reply_text(
                SETGOAL_SUCCESS_TEXT_TEMPLATE.format(
                    goal_text=goal_text, spreadsheet_url=spreadsheet_url
                ),
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        except Exception as e:
            await update.message.reply_text(SETGOAL_ERROR_TEXT)
            raise
        return ConversationHandler.END

    async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.message is not None
        await update.message.reply_text(CONVERSATION_CANCELLED_TEXT)
        return ConversationHandler.END

    return ConversationHandler(
        entry_points=[CommandHandler("setgoal", start)],
        states={
            TEXT_GOAL: [
                MessageHandler(filters.Text() & ~filters.Command(), input_goal)
            ],
            DEADLINE: [
                MessageHandler(filters.Text() & ~filters.Command(), input_deadline)
            ],
            AVAILABLE_TIME: [
                MessageHandler(
                    filters.Text() & ~filters.Command(), input_available_time
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        block=True,
        name="setgoal_conv",
        persistent=False,
    )
