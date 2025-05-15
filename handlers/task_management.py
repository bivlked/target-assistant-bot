"""Handlers for managing daily tasks, checking status, and motivation."""

from __future__ import annotations

from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from core.goal_manager import (
    GoalManager,
    USER_FACING_STATUS_DONE,
    USER_FACING_STATUS_NOT_DONE,
    USER_FACING_STATUS_PARTIAL,
)
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS
from utils.helpers import format_date
from core.metrics import USER_COMMANDS_TOTAL
from texts import (
    TODAY_TASK_DETAILS_TEMPLATE,
    NO_GOAL_FOR_TODAY_TEXT,
    NO_GOAL_FOR_STATUS_TEXT,
    SHEET_LINK_MARKDOWN_TEMPLATE,
    NO_TASK_FOR_CHECK_TEXT,
    CHECK_ALREADY_DONE_TEXT,
    PROMPT_CHECK_STATUS_TEMPLATE,
    CHECK_STATUS_UPDATED_TEXT,
)
import logging

CHOOSING_STATUS = 0

logger = logging.getLogger(__name__)


def build_task_handlers(goal_manager: GoalManager):
    """Builds and returns handlers related to daily task management.

    This includes handlers for /today, /status, /motivation, and the /check conversation.

    Args:
        goal_manager: Instance of GoalManager to interact with tasks and goals.

    Returns:
        A tuple containing the handler functions and ConversationHandler for these commands.
    """

    async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):  # noqa: D401
        """Handles the /today command, displaying the current day's task."""
        USER_COMMANDS_TOTAL.labels(command_name="/today").inc()
        assert update.effective_user is not None
        assert update.message is not None
        task = await goal_manager.get_today_task(update.effective_user.id)
        if task:
            text = TODAY_TASK_DETAILS_TEMPLATE.format(
                date=task[COL_DATE],
                day_of_week=task[COL_DAYOFWEEK],
                task=task[COL_TASK],
                status=task[COL_STATUS],
            )
        else:
            text = NO_GOAL_FOR_TODAY_TEXT
        await update.message.reply_text(text)

    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):  # noqa: D401
        """Handles the /status command, displaying goal progress and upcoming tasks."""
        USER_COMMANDS_TOTAL.labels(command_name="/status").inc()
        assert update.effective_user is not None
        assert update.message is not None
        data = await goal_manager.get_detailed_status(update.effective_user.id)

        if not data.get("goal") or data.get("total_days", 0) == 0:
            await update.message.reply_text(NO_GOAL_FOR_STATUS_TEXT)
            return

        msg_lines: list[str] = []
        msg_lines.append(f"🎯 *Цель*: {data['goal']}")
        msg_lines.append("")
        msg_lines.append(
            f"📊 *Прогресс*: {data['progress_percent']}%  (✅ {data['completed_days']}/{data['total_days']} дней)"
        )
        msg_lines.append(
            f"⏱ *Прошло*: {data['days_passed']} дн.   |   ⌛️ *Осталось*: {data['days_left']} дн."
        )

        upcoming = data.get("upcoming_tasks", [])
        if upcoming:
            msg_lines.append("")
            msg_lines.append("📝 *Ближайшие задачи*:")
            for i, task in enumerate(upcoming, 1):
                date = task.get(COL_DATE) or task.get("date")
                text = task.get(COL_TASK) or task.get("text")
                status = task.get(COL_STATUS) or task.get("status")
                status_emoji = "✅" if status == USER_FACING_STATUS_DONE else "⬜"
                msg_lines.append(f"{status_emoji} {i}. {date}: {text}")

        # Link to the spreadsheet
        msg_lines.append("")
        msg_lines.append(
            SHEET_LINK_MARKDOWN_TEMPLATE.format(sheet_url=data["sheet_url"])
        )

        await update.message.reply_text(
            "\n".join(msg_lines), parse_mode="Markdown", disable_web_page_preview=True
        )

    # ------------- CHECK -------------

    async def check_entry(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ):  # noqa: D401
        """Entry point for the /check conversation; displays today's task and status buttons."""
        USER_COMMANDS_TOTAL.labels(command_name="/check").inc()
        assert update.effective_user is not None
        assert update.message is not None
        task = await goal_manager.get_today_task(update.effective_user.id)
        if not task:
            await update.message.reply_text(NO_TASK_FOR_CHECK_TEXT)
            return ConversationHandler.END
        if task[COL_STATUS] == USER_FACING_STATUS_DONE:
            await update.message.reply_text(CHECK_ALREADY_DONE_TEXT)
            return ConversationHandler.END

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Выполнено", callback_data=USER_FACING_STATUS_DONE
                    ),
                    InlineKeyboardButton(
                        "❌ Не выполнено", callback_data=USER_FACING_STATUS_NOT_DONE
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "🤔 Частично", callback_data=USER_FACING_STATUS_PARTIAL
                    )
                ],
            ]
        )
        await update.message.reply_text(
            PROMPT_CHECK_STATUS_TEMPLATE.format(task_text=task[COL_TASK]),
            reply_markup=keyboard,
        )
        return CHOOSING_STATUS

    async def check_button(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ):  # noqa: D401
        """Handles button presses in the /check conversation to update task status."""
        query = update.callback_query
        assert query is not None
        await query.answer()
        status_val = str(query.data)
        assert update.effective_user is not None
        await goal_manager.batch_update_task_statuses(
            update.effective_user.id,
            {format_date(datetime.now()): status_val},
        )
        await query.edit_message_text(CHECK_STATUS_UPDATED_TEXT)
        return ConversationHandler.END

    async def motivation(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ):  # noqa: D401
        """Handles the /motivation command, sending a motivational message."""
        USER_COMMANDS_TOTAL.labels(command_name="/motivation").inc()
        assert update.effective_user is not None
        assert update.message is not None
        msg = await goal_manager.generate_motivation_message(update.effective_user.id)
        await update.message.reply_text(msg)

    check_conv = ConversationHandler(
        entry_points=[CommandHandler("check", check_entry)],
        states={CHOOSING_STATUS: [CallbackQueryHandler(check_button)]},
        fallbacks=[],
        name="check_conv",
        persistent=False,
    )

    return today, status, motivation, check_conv
