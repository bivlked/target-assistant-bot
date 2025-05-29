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
from utils.helpers import format_date, get_day_of_week
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
    user_id = update.effective_user.id
    sentry_sdk.set_tag("user_id", user_id)

    if not await is_subscribed(user_id):
        await update.message.reply_text(
            "❌ Вы не подписаны на бота. Используйте /start для начала."
        )
        return

    storage = get_async_storage()
    today = format_date(datetime.now(timezone.utc))

    # Get all tasks for today
    tasks = await storage.get_all_tasks_for_date(user_id, today)

    if not tasks:
        await update.message.reply_text(
            f"📅 *Задачи на {today}*\n\n"
            "У вас нет задач на сегодня.\n"
            "Используйте /my_goals для просмотра ваших целей.",
            parse_mode="Markdown",
        )
        return

    # Build message
    message = f"📅 *Задачи на {today}*\n\n"

    for task in tasks:
        status_emoji = {
            TaskStatus.DONE: "✅",
            TaskStatus.PARTIALLY_DONE: "🟡",
            TaskStatus.NOT_DONE: "⬜",
        }.get(task.status, "⬜")

        goal_name = task.goal_name or f"Цель {task.goal_id}"
        message += f"{status_emoji} *{goal_name}*\n"
        message += f"   📝 {task.task}\n\n"

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
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show overall progress."""
    USER_COMMANDS_TOTAL.labels(command_name="/status").inc()
    user_id = update.effective_user.id
    sentry_sdk.set_tag("user_id", user_id)

    if not await is_subscribed(user_id):
        await update.message.reply_text(
            "❌ Вы не подписаны на бота. Используйте /start для начала."
        )
        return

    storage = get_async_storage()
    stats = await storage.get_overall_statistics(user_id)

    if stats["total_goals"] == 0:
        await update.message.reply_text(
            "📊 У вас пока нет целей.\n"
            "Используйте /add_goal для создания новой цели."
        )
        return

    message = "📊 *Общий статус целей*\n\n"

    # Overall stats
    message += "📈 *Статистика:*\n"
    message += f"• Всего целей: {stats['total_goals']}\n"
    message += f"• Активных: {stats['active_count']}\n"
    message += f"• Завершенных: {stats['completed_count']}\n"

    if stats["active_count"] > 0:
        message += f"• Общий прогресс: {stats['total_progress']}%\n"
        message += "\n🎯 *Активные цели:*\n"

        for goal in stats["active_goals"]:
            priority_emoji = {"высокий": "🔴", "средний": "🟡", "низкий": "🟢"}.get(
                goal.priority.value, "🟡"
            )

            message += f"{priority_emoji} *{goal.name}*\n"
            message += f"   📊 {goal.progress_percent}% • 📅 {goal.deadline}\n"

    # Get upcoming tasks (next 3 days)
    upcoming_tasks = []
    today = datetime.now(timezone.utc)

    for i in range(3):
        date = format_date(today.replace(day=today.day + i))
        day_tasks = await storage.get_all_tasks_for_date(user_id, date)
        for task in day_tasks:
            if task.status != TaskStatus.DONE:
                upcoming_tasks.append((date, task))

    if upcoming_tasks:
        message += "\n📝 *Ближайшие задачи:*\n"
        for date, task in upcoming_tasks[:5]:  # Show max 5 tasks
            goal_name = task.goal_name or f"Цель {task.goal_id}"
            message += f"• {date}: {goal_name} - {task.task}\n"

    # Buttons
    keyboard = [
        [InlineKeyboardButton("📋 Мои цели", callback_data="back_to_goals")],
        [InlineKeyboardButton("📊 Открыть таблицу", callback_data="show_spreadsheet")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /check command - start task status update process."""
    USER_COMMANDS_TOTAL.labels(command_name="/check").inc()
    user_id = update.effective_user.id
    sentry_sdk.set_tag("user_id", user_id)

    if not await is_subscribed(user_id):
        await update.message.reply_text(
            "❌ Вы не подписаны на бота. Используйте /start для начала."
        )
        return ConversationHandler.END

    storage = get_async_storage()
    today = format_date(datetime.now(timezone.utc))

    # Get all tasks for today
    tasks = await storage.get_all_tasks_for_date(user_id, today)
    incomplete_tasks = [t for t in tasks if t.status != TaskStatus.DONE]

    if not incomplete_tasks:
        await update.message.reply_text(
            "✅ У вас нет невыполненных задач на сегодня!\n" "Отличная работа! 🎉"
        )
        return ConversationHandler.END

    if len(incomplete_tasks) == 1:
        # Single task - show status buttons directly
        task = incomplete_tasks[0]
        context.user_data["check_goal_id"] = task.goal_id
        context.user_data["check_date"] = today

        goal_name = task.goal_name or f"Цель {task.goal_id}"

        keyboard = [
            [
                InlineKeyboardButton("✅ Выполнено", callback_data="status_done"),
                InlineKeyboardButton("🟡 Частично", callback_data="status_partial"),
            ],
            [InlineKeyboardButton("❌ Не выполнено", callback_data="status_not_done")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📝 *Как дела с задачей?*\n\n"
            f"🎯 *Цель:* {goal_name}\n"
            f"📅 *Дата:* {today}\n"
            f"📋 *Задача:* {task.task}\n\n"
            f"Выберите статус выполнения:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

        return CHOOSING_STATUS
    else:
        # Multiple tasks - let user choose which to update
        keyboard = []
        for task in incomplete_tasks:
            goal_name = task.goal_name or f"Цель {task.goal_id}"
            button_text = f"{goal_name}: {task.task[:30]}..."
            keyboard.append(
                [
                    InlineKeyboardButton(
                        button_text, callback_data=f"goal_{task.goal_id}"
                    )
                ]
            )

        keyboard.append(
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_check")]
        )
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📝 *Выберите задачу для обновления статуса:*\n\n"
            f"У вас есть {len(incomplete_tasks)} невыполненных задач на сегодня.",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

        return CHOOSING_GOAL


async def choose_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle goal selection for status update."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_check":
        await query.edit_message_text("❌ Отмена обновления статуса.")
        return ConversationHandler.END

    goal_id = int(query.data.split("_")[1])
    user_id = query.from_user.id
    today = format_date(datetime.now(timezone.utc))

    context.user_data["check_goal_id"] = goal_id
    context.user_data["check_date"] = today

    storage = get_async_storage()
    task = await storage.get_task_for_date(user_id, goal_id, today)
    goal = await storage.get_goal_by_id(user_id, goal_id)

    if not task or not goal:
        await query.edit_message_text("❌ Задача не найдена.")
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton("✅ Выполнено", callback_data="status_done"),
            InlineKeyboardButton("🟡 Частично", callback_data="status_partial"),
        ],
        [InlineKeyboardButton("❌ Не выполнено", callback_data="status_not_done")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"📝 *Как дела с задачей?*\n\n"
        f"🎯 *Цель:* {goal.name}\n"
        f"📅 *Дата:* {today}\n"
        f"📋 *Задача:* {task.task}\n\n"
        f"Выберите статус выполнения:",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )

    return CHOOSING_STATUS


async def update_task_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Update task status and end conversation."""
    query = update.callback_query
    await query.answer()

    status_map = {
        "status_done": TaskStatus.DONE.value,
        "status_partial": TaskStatus.PARTIALLY_DONE.value,
        "status_not_done": TaskStatus.NOT_DONE.value,
    }

    new_status = status_map.get(query.data)
    if not new_status:
        await query.edit_message_text("❌ Неизвестный статус.")
        return ConversationHandler.END

    goal_id = context.user_data.get("check_goal_id")
    date = context.user_data.get("check_date")
    user_id = query.from_user.id

    if not goal_id or not date:
        await query.edit_message_text("❌ Ошибка: данные не найдены.")
        return ConversationHandler.END

    storage = get_async_storage()

    try:
        await storage.update_task_status(user_id, goal_id, date, new_status)

        status_text = {
            TaskStatus.DONE.value: "✅ Выполнено",
            TaskStatus.PARTIALLY_DONE.value: "🟡 Частично выполнено",
            TaskStatus.NOT_DONE.value: "❌ Не выполнено",
        }

        await query.edit_message_text(
            f"✅ Статус задачи обновлен: {status_text[new_status]}\n\n"
            f"Продолжайте в том же духе! 💪"
        )

    except Exception as e:
        logger.error("Error updating task status", exc_info=e)
        await query.edit_message_text(
            "❌ Произошла ошибка при обновлении статуса. Попробуйте позже."
        )

    return ConversationHandler.END


async def quick_status_update(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle quick status updates from /today command."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    if len(parts) != 3:
        return

    action, status, goal_id_str = parts
    goal_id = int(goal_id_str)
    user_id = query.from_user.id
    today = format_date(datetime.now(timezone.utc))

    status_map = {
        "done": TaskStatus.DONE.value,
        "partial": TaskStatus.PARTIALLY_DONE.value,
    }

    new_status = status_map.get(status)
    if not new_status:
        return

    storage = get_async_storage()

    try:
        await storage.update_task_status(user_id, goal_id, today, new_status)

        status_text = {
            TaskStatus.DONE.value: "✅ Выполнено",
            TaskStatus.PARTIALLY_DONE.value: "🟡 Частично выполнено",
        }

        await query.edit_message_text(
            f"✅ Статус задачи обновлен: {status_text[new_status]}\n\n"
            f"Отличная работа! 🎉"
        )

    except Exception as e:
        logger.error("Error updating task status", exc_info=e)
        await query.edit_message_text(
            "❌ Произошла ошибка при обновлении статуса. Попробуйте позже."
        )


async def motivation_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /motivation command - generate motivational message."""
    USER_COMMANDS_TOTAL.labels(command_name="/motivation").inc()
    user_id = update.effective_user.id
    sentry_sdk.set_tag("user_id", user_id)

    if not await is_subscribed(user_id):
        await update.message.reply_text(
            "❌ Вы не подписаны на бота. Используйте /start для начала."
        )
        return

    storage = get_async_storage()
    llm = get_async_llm()

    # Get active goals and their progress
    goals = await storage.get_active_goals(user_id)
    if not goals:
        await update.message.reply_text(
            "🎯 У вас пока нет активных целей.\n"
            "Создайте цель командой /add_goal для получения мотивации!"
        )
        return

    await update.message.reply_text("⏳ Генерирую мотивационное сообщение...")

    try:
        # Build context about goals and progress
        goal_info = "Мои цели:\n"
        progress_summary = "Прогресс:\n"

        for goal in goals:
            stats = await storage.get_goal_statistics(user_id, goal.goal_id)
            goal_info += f"- {goal.name}: {goal.description}\n"
            progress_summary += f"- {goal.name}: {stats.progress_percent}% ({stats.completed_tasks}/{stats.total_tasks} задач)\n"

        # Generate motivation
        motivation = await llm.generate_motivation(goal_info, progress_summary)

        await update.message.reply_text(
            f"💪 *Мотивация для вас:*\n\n{motivation}", parse_mode="Markdown"
        )

    except Exception as e:
        logger.error("Error generating motivation", exc_info=e)
        await update.message.reply_text(
            "❌ Не удалось получить мотивацию. Попробуйте позже."
        )


async def cancel_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel check conversation."""
    await update.message.reply_text("❌ Операция отменена.")
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
