"""Handlers for managing daily tasks with multi-goal support."""

from __future__ import annotations

import sentry_sdk
import structlog
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

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
            parse_mode="MarkdownV2",
        )
        return

    storage = get_async_storage()
    today_str = format_date(datetime.now(timezone.utc))

    # Get all tasks for today
    tasks = await storage.get_all_tasks_for_date(user_id, today_str)

    if not tasks:
        await update.message.reply_text(
            escape_markdown_v2(
                f"📅 *Задачи на {today_str}*\n\n"
                "У вас нет задач на сегодня.\n"
                "Используйте /my_goals для просмотра ваших целей."
            ),
            parse_mode="MarkdownV2",
        )
        return

    # Build message
    message = escape_markdown_v2(f"📅 *Задачи на {today_str}*\n\n")

    for task in tasks:
        status_emoji = {
            TaskStatus.DONE: "✅",
            TaskStatus.PARTIALLY_DONE: "🟡",
            TaskStatus.NOT_DONE: "⬜",
        }.get(task.status, "⬜")

        goal_name = escape_markdown_v2(task.goal_name or f"Цель {task.goal_id}")
        task_text = escape_markdown_v2(task.task)
        message += f"{status_emoji} *{goal_name}*\n"
        message += f"   📝 {task_text}\n\n"

    # Add quick check buttons
    keyboard = []
    if len(tasks) == 1:
        # Single task - direct status update
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
        # Multiple tasks - go to check menu
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
        message,
        parse_mode="MarkdownV2",
        reply_markup=reply_markup,
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show overall progress."""
    USER_COMMANDS_TOTAL.labels(command_name="/status").inc()

    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    sentry_sdk.set_tag("user_id", user_id)

    if not await is_subscribed(user_id):
        await update.message.reply_text(
            escape_markdown_v2(
                "❌ Вы не подписаны на бота. Используйте /start для начала."
            ),
            parse_mode="MarkdownV2",
        )
        return

    storage = get_async_storage()
    stats = await storage.get_overall_statistics(user_id)

    if stats["total_goals"] == 0:
        await update.message.reply_text(
            escape_markdown_v2(
                "📊 У вас пока нет целей.\n"
                "Используйте /add_goal для создания новой цели."
            ),
            parse_mode="MarkdownV2",
        )
        return

    message = escape_markdown_v2("📊 *Общий статус целей*\n\n")

    # Overall stats
    message += escape_markdown_v2("📈 *Статистика:*\n")
    message += escape_markdown_v2(f"• Всего целей: {stats['total_goals']}\n")
    message += escape_markdown_v2(f"• Активных: {stats['active_count']}\n")
    message += escape_markdown_v2(f"• Завершенных: {stats['completed_count']}\n")

    if stats["active_count"] > 0:
        message += escape_markdown_v2(f"• Общий прогресс: {stats['total_progress']}%\n")
        message += escape_markdown_v2("\n🎯 *Активные цели:*\n")

        for goal in stats["active_goals"]:
            priority_emoji = {"высокий": "🔴", "средний": "🟡", "низкий": "🟢"}.get(
                goal.priority.value, "🟡"
            )
            goal_name_escaped = escape_markdown_v2(goal.name)
            goal_deadline_escaped = escape_markdown_v2(goal.deadline)
            message += f"{priority_emoji} *{goal_name_escaped}*\n"
            message += escape_markdown_v2(
                f"   📊 {goal.progress_percent}% • 📅 {goal_deadline_escaped}\n"
            )

    # Get upcoming tasks (next 3 days)
    upcoming_tasks = []
    today_dt = datetime.now(timezone.utc)

    for i in range(3):
        date_str = format_date(today_dt.replace(day=today_dt.day + i))
        day_tasks = await storage.get_all_tasks_for_date(user_id, date_str)
        for task in day_tasks:
            if task.status != TaskStatus.DONE:
                upcoming_tasks.append((date_str, task))

    if upcoming_tasks:
        message += escape_markdown_v2("\n📝 *Ближайшие задачи:*\n")
        for date_str_item, task_item in upcoming_tasks[:5]:
            goal_name_escaped = escape_markdown_v2(
                task_item.goal_name or f"Цель {task_item.goal_id}"
            )
            task_text_escaped = escape_markdown_v2(task_item.task)
            date_str_escaped = escape_markdown_v2(date_str_item)
            message += escape_markdown_v2(
                f"• {date_str_escaped}: {goal_name_escaped} - {task_text_escaped}\n"
            )

    # Buttons
    keyboard = [
        [InlineKeyboardButton("📋 Мои цели", callback_data="back_to_goals")],
        [InlineKeyboardButton("📊 Открыть таблицу", callback_data="show_spreadsheet")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        message,
        parse_mode="MarkdownV2",
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
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    storage = get_async_storage()
    today_str = format_date(datetime.now(timezone.utc))

    # Get all tasks for today
    tasks = await storage.get_all_tasks_for_date(user_id, today_str)
    incomplete_tasks = [t for t in tasks if t.status != TaskStatus.DONE]

    if not incomplete_tasks:
        await update.message.reply_text(
            escape_markdown_v2(
                "✅ У вас нет невыполненных задач на сегодня!\n" "Отличная работа! 🎉"
            ),
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    if len(incomplete_tasks) == 1:
        # Single task - show status buttons directly
        task_item_check = incomplete_tasks[0]

        if not context.user_data:
            context.user_data = {}

        context.user_data["check_goal_id"] = task_item_check.goal_id
        context.user_data["check_date"] = today_str

        goal_name = escape_markdown_v2(
            task_item_check.goal_name or f"Цель {task_item_check.goal_id}"
        )
        task_text = escape_markdown_v2(task_item_check.task)

        keyboard = [
            [
                InlineKeyboardButton("✅ Выполнено", callback_data="status_done"),
                InlineKeyboardButton("🟡 Частично", callback_data="status_partial"),
            ],
            [InlineKeyboardButton("❌ Не выполнено", callback_data="status_not_done")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            escape_markdown_v2(
                f"📝 *Как дела с задачей?*\n\n"
                f"🎯 *Цель:* {goal_name}\n"
                f"�� *Дата:* {today_str}\n"
                f"📋 *Задача:* {task_text}\n\n"
                f"Выберите статус выполнения:"
            ),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup,
        )

        return CHOOSING_STATUS
    else:
        # Multiple tasks - let user choose which to update
        keyboard = []
        for task_loop_item in incomplete_tasks:
            goal_name = escape_markdown_v2(
                task_loop_item.goal_name or f"Цель {task_loop_item.goal_id}"
            )
            button_text = (
                f"{goal_name}: {escape_markdown_v2(task_loop_item.task[:30])}..."
            )
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

        await update.message.reply_text(
            escape_markdown_v2(
                f"📝 *Выберите задачу для обновления статуса:*\n\n"
                f"У вас есть {len(incomplete_tasks)} невыполненных задач на сегодня."
            ),
            parse_mode="MarkdownV2",
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
            escape_markdown_v2("❌ Отмена обновления статуса."), parse_mode="MarkdownV2"
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
            escape_markdown_v2("❌ Задача не найдена."), parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton("✅ Выполнено", callback_data="status_done"),
            InlineKeyboardButton("🟡 Частично", callback_data="status_partial"),
        ],
        [InlineKeyboardButton("❌ Не выполнено", callback_data="status_not_done")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    goal_name_escaped = escape_markdown_v2(goal_item_choose.name)
    task_text_escaped = escape_markdown_v2(task_item_choose.task)

    await query.edit_message_text(
        escape_markdown_v2(
            f"📝 *Как дела с задачей?*\n\n"
            f"🎯 *Цель:* {goal_name_escaped}\n"
            f"�� *Дата:* {today_str}\n"
            f"📋 *Задача:* {task_text_escaped}\n\n"
            f"Выберите статус выполнения:"
        ),
        parse_mode="MarkdownV2",
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

    new_status = status_map.get(query.data)
    if not new_status:
        await query.edit_message_text(
            escape_markdown_v2("❌ Неизвестный статус."), parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

    if not context.user_data:
        await query.edit_message_text(
            escape_markdown_v2("❌ Ошибка: данные не найдены."), parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

    goal_id = context.user_data.get("check_goal_id")
    date_str = context.user_data.get("check_date")
    user_id = query.from_user.id if query.from_user else 0

    if not goal_id or not date_str or not user_id:
        await query.edit_message_text(
            escape_markdown_v2("❌ Ошибка: данные не найдены."), parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

    storage = get_async_storage()

    try:
        await storage.update_task_status(user_id, goal_id, date_str, new_status)

        status_text_map = {
            TaskStatus.DONE.value: "✅ Выполнено",
            TaskStatus.PARTIALLY_DONE.value: "🟡 Частично выполнено",
            TaskStatus.NOT_DONE.value: "❌ Не выполнено",
        }

        await query.edit_message_text(
            escape_markdown_v2(
                f"✅ Статус задачи обновлен: {escape_markdown_v2(status_text_map[new_status])}\n\n"
                f"Отличная работа! 🎉"
            ),
            parse_mode="MarkdownV2",
        )

    except Exception as e:
        logger.error("Error updating task status", exc_info=e)
        await query.edit_message_text(
            escape_markdown_v2(
                "❌ Произошла ошибка при обновлении статуса. Попробуйте позже."
            ),
            parse_mode="MarkdownV2",
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

    action, status, goal_id_str = parts
    goal_id = int(goal_id_str)
    user_id = query.from_user.id if query.from_user else 0
    if not user_id:
        return

    today_str = format_date(datetime.now(timezone.utc))

    status_map_quick = {
        "done": TaskStatus.DONE.value,
        "partial": TaskStatus.PARTIALLY_DONE.value,
    }

    new_status = status_map_quick.get(status)
    if not new_status:
        return

    storage = get_async_storage()

    try:
        await storage.update_task_status(user_id, goal_id, today_str, new_status)

        status_text_map_quick = {
            TaskStatus.DONE.value: "✅ Выполнено",
            TaskStatus.PARTIALLY_DONE.value: "🟡 Частично выполнено",
        }

        await query.edit_message_text(
            escape_markdown_v2(
                f"✅ Статус задачи обновлен: {escape_markdown_v2(status_text_map_quick[new_status])}\n\n"
                f"Отличная работа! 🎉"
            ),
            parse_mode="MarkdownV2",
        )

    except Exception as e:
        logger.error("Error updating task status", exc_info=e)
        await query.edit_message_text(
            escape_markdown_v2(
                "❌ Произошла ошибка при обновлении статуса. Попробуйте позже."
            ),
            parse_mode="MarkdownV2",
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
            parse_mode="MarkdownV2",
        )
        return

    storage = get_async_storage()
    llm = get_async_llm()

    # Get active goals and their progress
    goals = await storage.get_active_goals(user_id)
    if not goals:
        await update.message.reply_text(
            escape_markdown_v2(
                "🎯 У вас пока нет активных целей.\n"
                "Создайте цель командой /add_goal для получения мотивации!"
            ),
            parse_mode="MarkdownV2",
        )
        return

    await update.message.reply_text(
        escape_markdown_v2("⏳ Генерирую мотивационное сообщение..."),
        parse_mode="MarkdownV2",
    )

    try:
        # Build context about goals and progress
        goal_info = "Мои цели:\n"
        progress_summary = "Прогресс:\n"

        for goal in goals:
            stats = await storage.get_goal_statistics(user_id, goal.goal_id)
            goal_name_escaped = escape_markdown_v2(goal.name)
            goal_desc_escaped = escape_markdown_v2(goal.description)
            goal_info += f"- {goal_name_escaped}: {goal_desc_escaped}\n"
            progress_summary += f"- {goal_name_escaped}: {stats.progress_percent}% ({stats.completed_tasks}/{stats.total_tasks} задач)\n"

        # Generate motivation
        motivation = await llm.generate_motivation(goal_info, progress_summary)
        motivation_escaped = escape_markdown_v2(motivation)

        await update.message.reply_text(
            f" *Мотивация для вас:*\n\n{motivation_escaped}", parse_mode="MarkdownV2"
        )

    except Exception as e:
        logger.error("Error generating motivation", exc_info=e)
        await update.message.reply_text(
            escape_markdown_v2("❌ Не удалось получить мотивацию. Попробуйте позже."),
            parse_mode="MarkdownV2",
        )


async def cancel_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel check conversation."""
    if update.message:
        await update.message.reply_text(
            escape_markdown_v2("❌ Операция отменена."), parse_mode="MarkdownV2"
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
