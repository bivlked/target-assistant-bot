"""Command handlers for multi-goal management."""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

from core.dependency_injection import get_async_llm, get_async_storage
from core.models import Goal, GoalPriority, GoalStatus, TaskStatus
from utils.helpers import format_date, get_day_of_week, escape_markdown_v2
from utils.subscription import is_subscribed
from sheets.client import PLAN_HEADERS

logger = structlog.get_logger(__name__)

# Conversation states
(
    GOAL_NAME,
    GOAL_DESCRIPTION,
    GOAL_DEADLINE,
    GOAL_DAILY_TIME,
    GOAL_PRIORITY,
    GOAL_TAGS,
    GOAL_CONFIRM,
    SELECT_GOAL,
    EDIT_FIELD,
    EDIT_VALUE,
) = range(10)


async def my_goals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's goals overview. Can be called from command or callback."""
    if update.callback_query:
        query = update.callback_query
        if not query or not query.from_user:
            return
        await query.answer()
        user_id = query.from_user.id

        # Callback query - edit message
        if not await is_subscribed(user_id):
            await query.edit_message_text(
                "❌ Вы не подписаны на бота. Используйте /start для начала."
            )
            return

        storage = get_async_storage()
        stats = await storage.get_overall_statistics(user_id)

        if stats["total_goals"] == 0:
            await query.edit_message_text(
                "📝 У вас пока нет целей.\n"
                "Используйте /add_goal для создания новой цели."
            )
            return

        # Build message
        message = "🎯 *Ваши цели:*\n\n"

        # Active goals
        if stats["active_count"] > 0:
            message += "✅ *Активные цели:*\n"
            for goal in stats["active_goals"]:
                status_emoji = (
                    "🔴"
                    if goal.priority == GoalPriority.HIGH
                    else "🟡" if goal.priority == GoalPriority.MEDIUM else "🟢"
                )
                message += f"{status_emoji} *{goal.name}* (ID: {goal.goal_id})\n"
                message += f"   📊 Прогресс: {goal.progress_percent}%\n"
                message += f"   📅 Дедлайн: {goal.deadline}\n"
                if goal.tags:
                    message += f"   🏷️ Теги: {', '.join(goal.tags)}\n"
                message += "\n"

        # Summary
        message += "\n📊 *Общая статистика:*\n"
        message += f"• Всего целей: {stats['total_goals']}\n"
        message += f"• Активных: {stats['active_count']}\n"
        message += f"• Завершенных: {stats['completed_count']}\n"
        message += f"• В архиве: {stats['archived_count']}\n"

        if stats["active_count"] > 0:
            message += f"• Общий прогресс: {stats['total_progress']}%\n"

        # Buttons
        keyboard = []

        if stats["can_add_more"]:
            keyboard.append(
                [InlineKeyboardButton("➕ Добавить цель", callback_data="add_goal")]
            )

        if stats["active_count"] > 0:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "📋 Управление целями", callback_data="manage_goals"
                    )
                ]
            )

        keyboard.append(
            [InlineKeyboardButton("📊 Таблица целей", callback_data="show_spreadsheet")]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    else:
        # Regular message
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id

        if not await is_subscribed(user_id):
            await update.message.reply_text(
                "❌ Вы не подписаны на бота. Используйте /start для начала."
            )
            return

        storage = get_async_storage()
        stats = await storage.get_overall_statistics(user_id)

        if stats["total_goals"] == 0:
            await update.message.reply_text(
                "📝 У вас пока нет целей.\n"
                "Используйте /add_goal для создания новой цели."
            )
            return

        # Build message
        message = "🎯 *Ваши цели:*\n\n"

        # Active goals
        if stats["active_count"] > 0:
            message += "✅ *Активные цели:*\n"
            for goal in stats["active_goals"]:
                status_emoji = (
                    "🔴"
                    if goal.priority == GoalPriority.HIGH
                    else "🟡" if goal.priority == GoalPriority.MEDIUM else "🟢"
                )
                message += f"{status_emoji} *{goal.name}* (ID: {goal.goal_id})\n"
                message += f"   📊 Прогресс: {goal.progress_percent}%\n"
                message += f"   📅 Дедлайн: {goal.deadline}\n"
                if goal.tags:
                    message += f"   🏷️ Теги: {', '.join(goal.tags)}\n"
                message += "\n"

        # Summary
        message += "\n📊 *Общая статистика:*\n"
        message += f"• Всего целей: {stats['total_goals']}\n"
        message += f"• Активных: {stats['active_count']}\n"
        message += f"• Завершенных: {stats['completed_count']}\n"
        message += f"• В архиве: {stats['archived_count']}\n"

        if stats["active_count"] > 0:
            message += f"• Общий прогресс: {stats['total_progress']}%\n"

        # Buttons
        keyboard = []

        if stats["can_add_more"]:
            keyboard.append(
                [InlineKeyboardButton("➕ Добавить цель", callback_data="add_goal")]
            )

        if stats["active_count"] > 0:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "📋 Управление целями", callback_data="manage_goals"
                    )
                ]
            )

        keyboard.append(
            [InlineKeyboardButton("📊 Таблица целей", callback_data="show_spreadsheet")]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )


async def add_goal_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start adding a new goal via CallbackQuery."""
    query = update.callback_query
    if not query or not query.from_user:
        return ConversationHandler.END

    await query.answer()
    user_id = query.from_user.id
    reply_method = query.edit_message_text
    message_to_reply = (
        query.message
    )  # For potential error messages not editing the current one

    storage = get_async_storage()
    active_count = await storage.get_active_goals_count(user_id)
    if active_count >= 10:
        await reply_method(
            escape_markdown_v2(
                "❌ Достигнут лимит активных целей (10).\n"
                "Завершите или архивируйте существующие цели перед добавлением новых."
            ),
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    await reply_method(
        escape_markdown_v2(
            "🎯 *Создание новой цели*\n\n"
            "Шаг 1/6: Введите короткое название цели (например: 'Изучить Python')"
        ),
        parse_mode="MarkdownV2",
    )
    return GOAL_NAME


async def add_goal_command_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Start adding a new goal via /add_goal command."""
    if not update.message or not update.effective_user:
        return ConversationHandler.END

    user_id = update.effective_user.id
    reply_method = update.message.reply_text

    # Check subscription status first for command entry
    if not await is_subscribed(user_id):
        await reply_method(
            escape_markdown_v2(
                "❌ Вы не подписаны на бота. Используйте /start для начала."
            ),
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    storage = get_async_storage()
    active_count = await storage.get_active_goals_count(user_id)
    if active_count >= 10:
        await reply_method(
            escape_markdown_v2(
                "❌ Достигнут лимит активных целей (10).\n"
                "Завершите или архивируйте существующие цели перед добавлением новых."
            ),
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    await reply_method(
        escape_markdown_v2(
            "🎯 *Создание новой цели*\n\n"
            "Шаг 1/6: Введите короткое название цели (например: 'Изучить Python')"
        ),
        parse_mode="MarkdownV2",
    )
    return GOAL_NAME


async def goal_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle goal name input."""
    # Убеждаемся что это текстовое сообщение, не callback
    if not update.message or not update.message.text:
        return GOAL_NAME  # Остаемся в том же состоянии

    goal_name = update.message.text.strip()
    if len(goal_name) < 3:
        await update.message.reply_text(
            "⚠️ Название цели должно содержать минимум 3 символа.\n"
            "Попробуйте еще раз:"
        )
        return GOAL_NAME

    context.user_data["goal_name"] = goal_name

    await update.message.reply_text(
        "Шаг 2/6: Опишите вашу цель подробнее.\n" "Что именно вы хотите достичь?"
    )

    return GOAL_DESCRIPTION


async def goal_description_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle goal description input."""
    # Убеждаемся что это текстовое сообщение
    if not update.message or not update.message.text:
        return GOAL_DESCRIPTION

    goal_description = update.message.text.strip()
    if len(goal_description) < 10:
        await update.message.reply_text(
            "⚠️ Описание цели должно быть более подробным (минимум 10 символов).\n"
            "Попробуйте еще раз:"
        )
        return GOAL_DESCRIPTION

    context.user_data["goal_description"] = goal_description

    await update.message.reply_text(
        "Шаг 3/6: Укажите срок достижения цели.\n"
        "Например: '3 месяца', '6 недель', '90 дней'"
    )

    return GOAL_DEADLINE


async def goal_deadline_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle goal deadline input."""
    # Убеждаемся что это текстовое сообщение
    if not update.message or not update.message.text:
        return GOAL_DEADLINE

    context.user_data["goal_deadline"] = update.message.text.strip()

    await update.message.reply_text(
        "Шаг 4/6: Сколько времени в день вы готовы уделять этой цели?\n"
        "Например: '1 час', '30 минут', '2 часа'"
    )

    return GOAL_DAILY_TIME


async def goal_daily_time_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle daily time input."""
    # Убеждаемся что это текстовое сообщение
    if not update.message or not update.message.text:
        return GOAL_DAILY_TIME

    context.user_data["goal_daily_time"] = update.message.text.strip()

    # Priority buttons
    keyboard = [
        [
            InlineKeyboardButton("🔴 Высокий", callback_data="priority_high"),
            InlineKeyboardButton("🟡 Средний", callback_data="priority_medium"),
            InlineKeyboardButton("🟢 Низкий", callback_data="priority_low"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Шаг 5/6: Выберите приоритет цели:",
        reply_markup=reply_markup,
    )

    return GOAL_PRIORITY


async def goal_priority_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle priority selection."""
    query = update.callback_query
    if not query or not query.data:
        return GOAL_PRIORITY

    await query.answer()

    priority_map = {
        "priority_high": GoalPriority.HIGH,
        "priority_medium": GoalPriority.MEDIUM,
        "priority_low": GoalPriority.LOW,
    }

    context.user_data["goal_priority"] = priority_map[query.data]

    await query.edit_message_text(
        "Шаг 6/6: Добавьте теги для цели (необязательно).\n"
        "Введите теги через запятую или отправьте '-' чтобы пропустить.\n"
        "Например: 'программирование, карьера, саморазвитие'"
    )

    return GOAL_TAGS


async def goal_tags_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle tags input and show confirmation."""
    # Убеждаемся что это текстовое сообщение
    if not update.message or not update.message.text:
        return GOAL_TAGS

    tags_text = update.message.text.strip()

    if tags_text == "-":
        tags = []
    else:
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

    context.user_data["goal_tags"] = tags

    # Show summary
    priority_text = {
        GoalPriority.HIGH: "🔴 Высокий",
        GoalPriority.MEDIUM: "🟡 Средний",
        GoalPriority.LOW: "🟢 Низкий",
    }

    summary = "📋 *Проверьте данные новой цели:*\n\n"
    summary += f"*Название:* {context.user_data['goal_name']}\n"
    summary += f"*Описание:* {context.user_data['goal_description']}\n"
    summary += f"*Срок:* {context.user_data['goal_deadline']}\n"
    summary += f"*Время в день:* {context.user_data['goal_daily_time']}\n"
    summary += f"*Приоритет:* {priority_text[context.user_data['goal_priority']]}\n"

    if tags:
        summary += f"*Теги:* {', '.join(tags)}\n"

    keyboard = [
        [
            InlineKeyboardButton("✅ Создать", callback_data="confirm_goal"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_goal"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        summary,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )

    return GOAL_CONFIRM


async def goal_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create the goal and generate plan."""
    query = update.callback_query
    if not query or not query.data or not query.from_user:
        return ConversationHandler.END

    await query.answer()

    if query.data == "cancel_goal":
        await query.edit_message_text("❌ Создание цели отменено.")
        return ConversationHandler.END

    user_id = query.from_user.id
    storage = get_async_storage()
    llm = get_async_llm()

    await query.edit_message_text(
        "⏳ Создаю цель и генерирую план достижения...\n"
        "Это может занять несколько секунд."
    )

    try:
        # Get next goal ID
        goal_id = await storage.get_next_goal_id(user_id)

        # Create goal object
        if not context.user_data or not all(
            key in context.user_data
            for key in [
                "goal_name",
                "goal_description",
                "goal_deadline",
                "goal_daily_time",
                "goal_priority",
                "goal_tags",
            ]
        ):
            if query:
                await query.edit_message_text(
                    escape_markdown_v2("❌ Ошибка: не все данные цели были собраны."),
                    parse_mode="MarkdownV2",
                )
            return ConversationHandler.END

        current_time_utc = datetime.now(timezone.utc)
        goal_start_date_str = format_date(current_time_utc)

        goal = Goal(
            goal_id=goal_id,
            name=context.user_data["goal_name"],
            description=context.user_data["goal_description"],
            deadline=context.user_data["goal_deadline"],
            daily_time=context.user_data["goal_daily_time"],
            start_date=goal_start_date_str,
            status=GoalStatus.ACTIVE,
            priority=context.user_data["goal_priority"],
            tags=context.user_data["goal_tags"],
            progress_percent=0,
        )

        # Save goal
        await storage.save_goal_info(user_id, goal)

        # Generate plan from LLM
        raw_plan_from_llm: List[Dict[str, Any]] = await llm.generate_plan(
            goal.description,
            goal.deadline,
            goal.daily_time,
        )

        # Transform plan to the format expected by SheetsManager
        start_date_dt = datetime.strptime(goal.start_date, "%d.%m.%Y").replace(
            tzinfo=timezone.utc
        )
        formatted_plan_for_sheets = []
        for i, item_from_llm in enumerate(raw_plan_from_llm):
            current_task_date_dt = start_date_dt + timedelta(days=i)
            task_description = item_from_llm.get(
                "task", item_from_llm.get("описание", "Нет описания задачи")
            )
            if not isinstance(task_description, str):
                task_description = str(task_description)

            formatted_plan_for_sheets.append(
                {
                    PLAN_HEADERS["Дата"]: format_date(current_task_date_dt),
                    PLAN_HEADERS["День недели"]: get_day_of_week(current_task_date_dt),
                    PLAN_HEADERS["Задача"]: task_description,
                    PLAN_HEADERS["Статус"]: TaskStatus.NOT_DONE.value,
                }
            )

        # Save plan
        await storage.save_plan(user_id, goal_id, formatted_plan_for_sheets)

        # Calculate total days from the formatted plan that was actually saved
        total_days = len(formatted_plan_for_sheets)

        await query.edit_message_text(
            f"✅ Цель '{goal.name}' успешно создана!\n\n"
            f"📅 План составлен на {total_days} дней.\n"
            f"🚀 Начинайте выполнение уже сегодня!\n\n"
            f"Используйте /today чтобы увидеть задачи на сегодня."
        )

    except Exception as e:
        logger.error("Error creating goal", exc_info=e)
        await query.edit_message_text(
            "❌ Произошла ошибка при создании цели.\n" "Попробуйте еще раз позже."
        )

    return ConversationHandler.END


async def manage_goals_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show goals management menu."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    await query.answer()

    user_id = query.from_user.id
    storage = get_async_storage()

    goals = await storage.get_active_goals(user_id)

    if not goals:
        await query.edit_message_text("У вас нет активных целей.")
        return

    keyboard = []

    # Add button for each goal
    for goal in goals:
        emoji = (
            "🔴"
            if goal.priority == GoalPriority.HIGH
            else "🟡" if goal.priority == GoalPriority.MEDIUM else "🟢"
        )
        button_text = f"{emoji} {goal.name} ({goal.progress_percent}%)"
        keyboard.append(
            [InlineKeyboardButton(button_text, callback_data=f"goal_{goal.goal_id}")]
        )

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_goals")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📋 Выберите цель для управления:",
        reply_markup=reply_markup,
    )


async def show_goal_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed information about a specific goal."""
    query = update.callback_query
    if not query or not query.data or not query.from_user:
        return

    await query.answer()

    goal_id = int(query.data.split("_")[1])
    user_id = query.from_user.id
    storage = get_async_storage()

    goal = await storage.get_goal_by_id(user_id, goal_id)
    if not goal:
        await query.edit_message_text("Цель не найдена.")
        return

    stats = await storage.get_goal_statistics(user_id, goal_id)

    priority_text = {
        GoalPriority.HIGH: "🔴 Высокий",
        GoalPriority.MEDIUM: "🟡 Средний",
        GoalPriority.LOW: "🟢 Низкий",
    }

    status_text = {
        GoalStatus.ACTIVE: "✅ Активная",
        GoalStatus.COMPLETED: "🏆 Завершенная",
        GoalStatus.ARCHIVED: "📦 В архиве",
    }

    message = f"🎯 *{goal.name}*\n\n"
    message += f"*Описание:* {goal.description}\n"
    message += f"*Статус:* {status_text[goal.status]}\n"
    message += f"*Приоритет:* {priority_text[goal.priority]}\n"
    message += f"*Срок:* {goal.deadline}\n"
    message += f"*Время в день:* {goal.daily_time}\n"
    message += f"*Начало:* {goal.start_date}\n"

    if goal.tags:
        message += f"*Теги:* {', '.join(goal.tags)}\n"

    message += "\n📊 *Статистика:*\n"
    message += f"• Прогресс: {stats.progress_percent}%\n"
    message += f"• Выполнено задач: {stats.completed_tasks} из {stats.total_tasks}\n"
    message += f"• Дней прошло: {stats.days_elapsed}\n"
    message += f"• Дней осталось: {stats.days_remaining}\n"

    if stats.is_on_track:
        message += "• ✅ Идете по плану\n"
    else:
        message += "• ⚠️ Отстаете от плана\n"

    keyboard = [
        [
            InlineKeyboardButton(
                "📝 Редактировать", callback_data=f"edit_goal_{goal_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Посмотреть план", callback_data=f"view_plan_{goal_id}"
            )
        ],
    ]

    if goal.status == GoalStatus.ACTIVE:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "✅ Завершить", callback_data=f"complete_goal_{goal_id}"
                ),
                InlineKeyboardButton(
                    "📦 В архив", callback_data=f"archive_goal_{goal_id}"
                ),
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_goal_{goal_id}"),
            InlineKeyboardButton("⬅️ Назад", callback_data="manage_goals"),
        ]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def complete_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark goal as completed."""
    query = update.callback_query
    if not query or not query.data or not query.from_user:
        return

    await query.answer()

    goal_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    storage = get_async_storage()

    await storage.update_goal_status(user_id, goal_id, GoalStatus.COMPLETED)

    await query.edit_message_text(
        "🏆 Поздравляем! Цель успешно завершена!\n\n" "Вы проделали отличную работу! 🎉"
    )


async def archive_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Archive a goal."""
    query = update.callback_query
    if not query or not query.data or not query.from_user:
        return

    await query.answer()

    goal_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    storage = get_async_storage()

    await storage.archive_goal(user_id, goal_id)

    await query.edit_message_text("📦 Цель перемещена в архив.")


async def delete_goal_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show deletion confirmation."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    goal_id = int(query.data.split("_")[2])

    keyboard = [
        [
            InlineKeyboardButton(
                "⚠️ Да, удалить", callback_data=f"delete_goal_yes_{goal_id}"
            ),
            InlineKeyboardButton("❌ Отмена", callback_data="manage_goals"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "⚠️ *Внимание!*\n\n"
        "Вы уверены, что хотите удалить эту цель?\n"
        "Все связанные задачи и прогресс будут удалены безвозвратно.",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def delete_goal_execute(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Delete goal after confirmation."""
    query = update.callback_query
    if not query or not query.data or not query.from_user:
        return

    await query.answer()

    goal_id = int(query.data.split("_")[3])
    user_id = query.from_user.id
    storage = get_async_storage()

    await storage.delete_goal(user_id, goal_id)

    await query.edit_message_text("🗑️ Цель удалена.")


async def show_spreadsheet_link(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show spreadsheet link."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    await query.answer()

    user_id = query.from_user.id
    storage = get_async_storage()

    # Используем новый метод для получения URL
    spreadsheet_url = await storage.get_spreadsheet_url(user_id)

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_goals")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"📊 *Ваша таблица целей:*\n\n{spreadsheet_url}",
        parse_mode="Markdown",
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )


async def cancel_conversation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancel goal creation conversation."""
    if update.message:
        await update.message.reply_text("❌ Операция отменена.")
    return ConversationHandler.END


# Create conversation handler for adding goals
add_goal_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(add_goal_start, pattern="^add_goal$"),
        CommandHandler("add_goal", add_goal_command_start),  # Added CommandHandler
    ],
    states={
        GOAL_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, goal_name_received)
        ],
        GOAL_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, goal_description_received)
        ],
        GOAL_DEADLINE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, goal_deadline_received)
        ],
        GOAL_DAILY_TIME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, goal_daily_time_received)
        ],
        GOAL_PRIORITY: [
            CallbackQueryHandler(goal_priority_received, pattern="^priority_")
        ],
        GOAL_TAGS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, goal_tags_received)
        ],
        GOAL_CONFIRM: [
            CallbackQueryHandler(goal_confirmed, pattern="^(confirm|cancel)_goal$")
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversation),
        CommandHandler("my_goals", cancel_conversation),  # Allow going back
    ],
    per_message=False,
    conversation_timeout=300,  # 5 minutes timeout
)


def get_goals_handlers():
    """Get all goals-related handlers."""
    return [
        CommandHandler("my_goals", my_goals_command),
        add_goal_conversation,
        CallbackQueryHandler(manage_goals_menu, pattern="^manage_goals$"),
        CallbackQueryHandler(show_goal_details, pattern="^goal_\\d+$"),
        CallbackQueryHandler(complete_goal, pattern="^complete_goal_\\d+$"),
        CallbackQueryHandler(archive_goal, pattern="^archive_goal_\\d+$"),
        CallbackQueryHandler(delete_goal_confirm, pattern="^delete_goal_\\d+$"),
        CallbackQueryHandler(delete_goal_execute, pattern="^delete_goal_yes_\\d+$"),
        CallbackQueryHandler(show_spreadsheet_link, pattern="^show_spreadsheet$"),
        CallbackQueryHandler(my_goals_command, pattern="^back_to_goals$"),
    ]
