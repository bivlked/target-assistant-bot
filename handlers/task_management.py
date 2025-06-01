"""Handlers for managing daily tasks with multi-goal support."""

from __future__ import annotations

import sentry_sdk
import structlog
from datetime import datetime, timezone
from typing import Optional, Callable

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)
from telegram.constants import ParseMode

from core.dependency_injection import get_async_storage, get_async_llm
from core.models import Goal, GoalStatus, TaskStatus
from utils.helpers import format_date, get_day_of_week, escape_markdown_v2
from utils.subscription import is_subscribed
from core.metrics import USER_COMMANDS_TOTAL

logger = structlog.get_logger(__name__)

# Conversation states
CHOOSING_STATUS, CHOOSING_GOAL, CHOOSING_TASK = range(3)

# Status mapping
STATUS_MAPPING = {
    "done": TaskStatus.DONE.value,
    "not_done": TaskStatus.NOT_DONE.value,
    "partial": TaskStatus.PARTIALLY_DONE.value,
}


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /today command - show all tasks for today."""
    USER_COMMANDS_TOTAL.labels(command_name="/today").inc()

    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    sentry_sdk.set_tag("user_id", user_id)

    if not await is_subscribed(user_id):
        await update.message.reply_text(
            escape_markdown_v2(
                "❌ Вы не подписаны на бота. Используйте /start для начала."
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    storage = get_async_storage()
    today_str = format_date(datetime.now(timezone.utc))

    tasks = await storage.get_all_tasks_for_date(user_id, today_str)

    if not tasks:
        message_text = (
            f"📅 *Задачи на {today_str}*\n\n"
            "У вас нет задач на сегодня.\n"
            "Используйте /my_goals для просмотра ваших целей."
        )
        await update.message.reply_text(
            escape_markdown_v2(message_text), parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    message_parts = [f"📅 *Задачи на {today_str}*\n\n"]
    for task in tasks:
        status_emoji = {
            TaskStatus.DONE: "✅",
            TaskStatus.PARTIALLY_DONE: "🟡",
            TaskStatus.NOT_DONE: "⬜",
        }.get(task.status, "⬜")
        message_parts.append(
            f"{status_emoji} *{task.goal_name or f'Цель {task.goal_id}'}*\n   📝 {task.task}\n\n"
        )

    full_message = "".join(message_parts)

    keyboard = []
    if len(tasks) == 1:
        task = tasks[0]
        if task.status != TaskStatus.DONE:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "✅ Выполнено", callback_data=f"quick_done_{task.goal_id}"
                    ),
                    InlineKeyboardButton(
                        "🟡 Частично", callback_data=f"quick_partial_{task.goal_id}"
                    ),
                ]
            ]
    else:
        keyboard = [
            [
                InlineKeyboardButton(
                    "📝 Отметить выполнение", callback_data="check_tasks"
                )
            ]
        ]

    keyboard.append(
        [InlineKeyboardButton("📊 Общий статус", callback_data="overall_status")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        escape_markdown_v2(full_message),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show overall progress."""
    USER_COMMANDS_TOTAL.labels(command_name="/status").inc()

    query = update.callback_query
    is_callback = query is not None

    effective_user: Optional[User] = None
    reply_method: Optional[Callable] = None
    edit_method: Optional[Callable] = None

    if is_callback and query:
        if not query.from_user:
            return
        await query.answer()
        effective_user = query.from_user
        if query.message:  # query.message can be None
            edit_method = query.edit_message_text
            # Fallback to send_message if message is not available to edit (e.g. too old)
            # or if we prefer sending a new message for callbacks in some cases.
            # For now, we primarily try to edit.
    elif update.message and update.effective_user:
        effective_user = update.effective_user
        reply_method = update.message.reply_text
    else:
        logger.warning("status_command called with no user or message/query context")
        return

    if not effective_user:
        logger.warning("No effective_user in status_command")
        return

    user_id = effective_user.id
    sentry_sdk.set_tag("user_id", user_id)

    if not await is_subscribed(user_id):
        err_msg = escape_markdown_v2(
            "❌ Вы не подписаны на бота. Используйте /start для начала."
        )
        if edit_method:
            await edit_method(text=err_msg, parse_mode=ParseMode.MARKDOWN_V2)
        elif reply_method:
            await reply_method(text=err_msg, parse_mode=ParseMode.MARKDOWN_V2)
        return

    storage = get_async_storage()
    stats = await storage.get_overall_statistics(user_id)

    if stats["total_goals"] == 0:
        no_goals_msg = escape_markdown_v2(
            "📊 У вас пока нет целей.\n"
            "Используйте /add_goal для создания новой цели."
        )
        if edit_method:
            await edit_method(text=no_goals_msg, parse_mode=ParseMode.MARKDOWN_V2)
        elif reply_method:
            await reply_method(text=no_goals_msg, parse_mode=ParseMode.MARKDOWN_V2)
        return

    message_parts = []
    message_parts.append("📊 *Общий статус целей*\n\n")
    message_parts.append("📈 *Статистика:*\n")
    message_parts.append(f"• Всего целей: {stats['total_goals']}\n")
    message_parts.append(f"• Активных: {stats['active_count']}\n")
    message_parts.append(f"• Завершенных: {stats['completed_count']}\n")
    message_parts.append(f"• В архиве: {stats.get('archived_count', 0)}\n")

    if stats["active_count"] > 0:
        message_parts.append(f"• Общий прогресс: {stats['total_progress']}%\n")
        message_parts.append("\n🎯 *Активные цели:*\n")
        for goal_stat_item in stats["active_goals"]:
            priority_emoji = {"высокий": "🔴", "средний": "🟡", "низкий": "🟢"}.get(
                goal_stat_item.priority.value, "🟡"
            )
            message_parts.append(f"{priority_emoji} *{goal_stat_item.name}*\n")
            message_parts.append(
                f"   📊 {goal_stat_item.progress_percent}% • 📅 {goal_stat_item.deadline}\n"
            )

    upcoming_tasks_parts = []
    today_dt = datetime.now(timezone.utc)
    for i in range(3):
        date_str = format_date(today_dt.replace(day=today_dt.day + i))
        day_tasks = await storage.get_all_tasks_for_date(user_id, date_str)
        for task_stat_item in day_tasks:
            if task_stat_item.status != TaskStatus.DONE:
                upcoming_tasks_parts.append(
                    f"• {date_str}: {task_stat_item.goal_name or f'Цель {task_stat_item.goal_id}'} - {task_stat_item.task}\n"
                )

    if upcoming_tasks_parts:
        message_parts.append("\n📝 *Ближайшие задачи:*\n")
        message_parts.extend(upcoming_tasks_parts[:5])

    full_message = escape_markdown_v2("".join(message_parts))

    keyboard = [
        [InlineKeyboardButton("📋 Мои цели", callback_data="back_to_goals")],
        [InlineKeyboardButton("📊 Открыть таблицу", callback_data="show_spreadsheet")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if edit_method:
        await edit_method(
            text=full_message,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )
    elif reply_method:
        await reply_method(
            text=full_message,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )
    else:  # Fallback if no method determined (should not happen with prior checks)
        logger.error(
            "No reply/edit method determined in status_command", user_id=user_id
        )
        # Consider sending a new message via context.bot.send_message as a last resort
        if context.bot:
            await context.bot.send_message(
                chat_id=user_id,
                text=full_message,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup,
            )


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /check command - start task status update process."""
    USER_COMMANDS_TOTAL.labels(command_name="/check").inc()

    if not update.effective_user or not update.message:
        return ConversationHandler.END

    user_id = update.effective_user.id
    sentry_sdk.set_tag("user_id", user_id)

    if not await is_subscribed(user_id):
        await update.message.reply_text(
            escape_markdown_v2(
                "❌ Вы не подписаны на бота. Используйте /start для начала."
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return ConversationHandler.END

    storage = get_async_storage()
    today_str = format_date(datetime.now(timezone.utc))

    tasks = await storage.get_all_tasks_for_date(user_id, today_str)
    incomplete_tasks = [t for t in tasks if t.status != TaskStatus.DONE]

    if not incomplete_tasks:
        message_text = (
            "✅ У вас нет невыполненных задач на сегодня!\nОтличная работа! 🎉"
        )
        await update.message.reply_text(
            escape_markdown_v2(message_text), parse_mode=ParseMode.MARKDOWN_V2
        )
        return ConversationHandler.END

    if len(incomplete_tasks) == 1:
        task_item_check = incomplete_tasks[0]
        if not context.user_data:
            context.user_data = {}
        context.user_data["check_goal_id"] = task_item_check.goal_id
        context.user_data["check_date"] = today_str

        message_text = (
            f"📝 *Как дела с задачей?*\n\n"
            f"🎯 *Цель:* {task_item_check.goal_name or f'Цель {task_item_check.goal_id}'}\n"
            f"📅 *Дата:* {today_str}\n"
            f"📋 *Задача:* {task_item_check.task}\n\n"
            f"Выберите статус выполнения:"
        )
        keyboard = [
            [
                InlineKeyboardButton("✅ Выполнено", callback_data="status_done"),
                InlineKeyboardButton("🟡 Частично", callback_data="status_partial"),
            ],
            [InlineKeyboardButton("❌ Не выполнено", callback_data="status_not_done")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            escape_markdown_v2(message_text),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )
        return CHOOSING_STATUS
    else:
        keyboard = []
        for task_loop_item in incomplete_tasks:
            goal_name_escaped = escape_markdown_v2(
                task_loop_item.goal_name or f"Цель {task_loop_item.goal_id}"
            )
            task_text_preview_escaped = escape_markdown_v2(task_loop_item.task[:30])
            button_text = f"{goal_name_escaped}: {task_text_preview_escaped}..."
            keyboard.append(
                [
                    InlineKeyboardButton(
                        button_text, callback_data=f"goal_{task_loop_item.goal_id}"
                    )
                ]
            )
        keyboard.append(
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_check")]
        )
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text_parts = [
            "📝 *Выберите задачу для обновления статуса:*\n\n",
            f"У вас есть {len(incomplete_tasks)} невыполненных задач на сегодня\.",
        ]
        await update.message.reply_text(
            escape_markdown_v2("".join(message_text_parts)),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )
        return CHOOSING_GOAL


async def choose_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle goal selection for status update."""
    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END
    await query.answer()

    if query.data == "cancel_check":
        await query.edit_message_text(
            escape_markdown_v2("❌ Отмена обновления статуса."),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return ConversationHandler.END

    goal_id = int(query.data.split("_")[1])
    user_id = query.from_user.id if query.from_user else 0
    if not user_id:
        return ConversationHandler.END

    today_str = format_date(datetime.now(timezone.utc))
    if not context.user_data:
        context.user_data = {}
    context.user_data["check_goal_id"] = goal_id
    context.user_data["check_date"] = today_str

    storage = get_async_storage()
    task_item_choose = await storage.get_task_for_date(user_id, goal_id, today_str)
    goal_item_choose = await storage.get_goal_by_id(user_id, goal_id)

    if not task_item_choose or not goal_item_choose:
        await query.edit_message_text(
            escape_markdown_v2("❌ Задача не найдена."),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return ConversationHandler.END

    message_text = (
        f"📝 *Как дела с задачей?*\n\n"
        f"🎯 *Цель:* {goal_item_choose.name}\n"
        f"📅 *Дата:* {today_str}\n"
        f"📋 *Задача:* {task_item_choose.task}\n\n"
        f"Выберите статус выполнения:"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ Выполнено", callback_data="status_done"),
            InlineKeyboardButton("🟡 Частично", callback_data="status_partial"),
        ],
        [InlineKeyboardButton("❌ Не выполнено", callback_data="status_not_done")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        escape_markdown_v2(message_text),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
    )
    return CHOOSING_STATUS


async def update_task_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Update task status and end conversation."""
    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END
    await query.answer()

    status_map = {
        "status_done": TaskStatus.DONE.value,
        "status_partial": TaskStatus.PARTIALLY_DONE.value,
        "status_not_done": TaskStatus.NOT_DONE.value,
    }
    new_status_value = status_map.get(query.data)
    if not new_status_value:
        await query.edit_message_text(
            escape_markdown_v2("❌ Неизвестный статус."),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return ConversationHandler.END

    if not context.user_data:
        await query.edit_message_text(
            escape_markdown_v2("❌ Ошибка: данные не найдены."),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return ConversationHandler.END

    goal_id = context.user_data.get("check_goal_id")
    date_str = context.user_data.get("check_date")
    user_id = query.from_user.id if query.from_user else 0

    if not goal_id or not date_str or not user_id:
        await query.edit_message_text(
            escape_markdown_v2("❌ Ошибка: данные не найдены."),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return ConversationHandler.END

    storage = get_async_storage()
    try:
        await storage.update_task_status(user_id, goal_id, date_str, new_status_value)
        status_text_map = {
            TaskStatus.DONE.value: "✅ Выполнено",
            TaskStatus.PARTIALLY_DONE.value: "🟡 Частично выполнено",
            TaskStatus.NOT_DONE.value: "❌ Не выполнено",
        }
        message_text = (
            f"{status_text_map[new_status_value]}\n\n" f"Продолжайте в том же духе! 💪"
        )
        await query.edit_message_text(
            escape_markdown_v2(message_text), parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error("Error updating task status", exc_info=e)
        await query.edit_message_text(
            escape_markdown_v2(
                "❌ Произошла ошибка при обновлении статуса. Попробуйте позже."
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    return ConversationHandler.END


async def quick_status_update(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle quick status updates from /today command."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split("_")
    if len(parts) != 3:
        return

    action, status_key, goal_id_str = parts
    goal_id = int(goal_id_str)
    user_id = query.from_user.id if query.from_user else 0
    if not user_id:
        return

    today_str = format_date(datetime.now(timezone.utc))
    status_map_quick = {
        "done": TaskStatus.DONE.value,
        "partial": TaskStatus.PARTIALLY_DONE.value,
    }
    new_status_value = status_map_quick.get(status_key)
    if not new_status_value:
        return

    storage = get_async_storage()
    try:
        await storage.update_task_status(user_id, goal_id, today_str, new_status_value)
        status_text_map_quick = {
            TaskStatus.DONE.value: "✅ Выполнено",
            TaskStatus.PARTIALLY_DONE.value: "🟡 Частично выполнено",
        }
        message_text = (
            f"{status_text_map_quick[new_status_value]}\n\n" f"Отличная работа! 🎉"
        )
        await query.edit_message_text(
            escape_markdown_v2(message_text), parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error("Error updating task status", exc_info=e)
        await query.edit_message_text(
            escape_markdown_v2(
                "❌ Произошла ошибка при обновлении статуса. Попробуйте позже."
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def motivation_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /motivation command - generate motivational message."""
    USER_COMMANDS_TOTAL.labels(command_name="/motivation").inc()

    if not update.effective_user or not update.message:
        return
    user_id = update.effective_user.id
    sentry_sdk.set_tag("user_id", user_id)

    if not await is_subscribed(user_id):
        await update.message.reply_text(
            escape_markdown_v2(
                "❌ Вы не подписаны на бота. Используйте /start для начала."
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    storage = get_async_storage()
    llm = get_async_llm()
    goals = await storage.get_active_goals(user_id)

    if not goals:
        message_text = (
            "🎯 У вас пока нет активных целей.\n"
            "Создайте цель командой /add_goal для получения мотивации!"
        )
        await update.message.reply_text(
            escape_markdown_v2(message_text), parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    await update.message.reply_text(
        escape_markdown_v2("⏳ Генерирую мотивационное сообщение..."),
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    try:
        goal_info_parts = ["Мои цели:"]
        progress_summary_parts = ["Прогресс:"]
        for goal_item in goals:
            stats = await storage.get_goal_statistics(user_id, goal_item.goal_id)
            goal_name_escaped = escape_markdown_v2(goal_item.name)
            goal_desc_escaped = escape_markdown_v2(goal_item.description)
            goal_info_parts.append(f"\- {goal_name_escaped}: {goal_desc_escaped}")
            progress_summary_parts.append(
                f"\- {goal_name_escaped}: {stats.progress_percent}% ({stats.completed_tasks}/{stats.total_tasks} задач)"
            )

        goal_info = "\n".join(goal_info_parts)
        progress_summary = "\n".join(progress_summary_parts)

        motivation_text = await llm.generate_motivation(goal_info, progress_summary)
        message_to_send = (
            f"💪 *Мотивация для вас:*\n\n{escape_markdown_v2(motivation_text)}"
        )
        await update.message.reply_text(
            message_to_send, parse_mode=ParseMode.MARKDOWN_V2
        )

    except Exception as e:
        logger.error("Error generating motivation", exc_info=e)
        await update.message.reply_text(
            escape_markdown_v2("❌ Не удалось получить мотивацию. Попробуйте позже."),
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def cancel_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel check conversation."""
    if update.message:
        await update.message.reply_text(
            escape_markdown_v2("❌ Операция отменена."),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    return ConversationHandler.END


# Create conversation handler for check command
check_conversation = ConversationHandler(
    entry_points=[CommandHandler("check", check_command)],
    states={
        CHOOSING_GOAL: [
            CallbackQueryHandler(choose_goal, pattern="^(goal_\\d+|cancel_check)$")
        ],
        CHOOSING_STATUS: [
            CallbackQueryHandler(
                update_task_status, pattern="^status_(done|partial|not_done)$"
            )
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_check)],
)


def get_task_handlers():
    """Get all task management handlers."""
    return [
        CommandHandler("today", today_command),
        CommandHandler("status", status_command),
        CommandHandler("motivation", motivation_command),
        check_conversation,
        CallbackQueryHandler(
            quick_status_update, pattern="^quick_(done|partial)_\\d+$"
        ),
        CallbackQueryHandler(status_command, pattern="^overall_status$"),
        CallbackQueryHandler(check_command, pattern="^check_tasks$"),
    ]
