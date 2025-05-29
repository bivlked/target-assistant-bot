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

from core.dependency_injection import get_async_llm, get_async_storage
from core.models import Goal, GoalPriority, GoalStatus, TaskStatus
from utils.helpers import format_date, get_day_of_week
from utils.subscription import is_subscribed

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
    """Handle /my_goals command - show all user goals."""
    # Handle both message and callback query
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        send_message = query.edit_message_text
    else:
        user_id = update.effective_user.id
        send_message = update.message.reply_text

    if not await is_subscribed(user_id):
        await send_message("❌ Вы не подписаны на бота. Используйте /start для начала.")
        return

    storage = get_async_storage()
    stats = await storage.get_overall_statistics(user_id)

    if stats["total_goals"] == 0:
        await send_message(
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
            [InlineKeyboardButton("📋 Управление целями", callback_data="manage_goals")]
        )

    keyboard.append(
        [InlineKeyboardButton("📊 Таблица целей", callback_data="show_spreadsheet")]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_message(
        message,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def add_goal_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start adding a new goal."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    storage = get_async_storage()

    # Check goal limit
    active_count = await storage.get_active_goals_count(user_id)
    if active_count >= 10:
        await query.edit_message_text(
            "❌ Достигнут лимит активных целей (10).\n"
            "Завершите или архивируйте существующие цели перед добавлением новых."
        )
        return ConversationHandler.END

    await query.edit_message_text(
        "🎯 *Создание новой цели*\n\n"
        "Шаг 1/6: Введите короткое название цели (например: 'Изучить Python')",
        parse_mode="Markdown",
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
        from datetime import datetime, timezone

        goal = Goal(
            goal_id=goal_id,
            name=context.user_data["goal_name"],
            description=context.user_data["goal_description"],
            deadline=context.user_data["goal_deadline"],
            daily_time=context.user_data["goal_daily_time"],
            start_date=format_date(datetime.now(timezone.utc)),
            status=GoalStatus.ACTIVE,
            priority=context.user_data["goal_priority"],
            tags=context.user_data["goal_tags"],
            progress_percent=0,
        )

        # Save goal
        await storage.save_goal_info(user_id, goal)

        # Generate plan
        plan = await llm.generate_plan(
            goal.description,
            goal.deadline,
            goal.daily_time,
        )

        # Save plan
        await storage.save_plan(user_id, goal_id, plan)

        # Calculate total days
        total_days = len(plan)

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
    await query.answer()

    goal_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    storage = get_async_storage()

    await storage.archive_goal(user_id, goal_id)

    await query.edit_message_text("📦 Цель перемещена в архив.")


async def delete_goal_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Confirm goal deletion."""
    query = update.callback_query
    await query.answer()

    goal_id = int(query.data.split("_")[2])

    keyboard = [
        [
            InlineKeyboardButton(
                "⚠️ Да, удалить", callback_data=f"delete_goal_yes_{goal_id}"
            ),
            InlineKeyboardButton("❌ Отмена", callback_data=f"goal_{goal_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "⚠️ Вы уверены, что хотите удалить эту цель?\n" "Это действие нельзя отменить!",
        reply_markup=reply_markup,
    )


async def delete_goal_execute(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Execute goal deletion."""
    query = update.callback_query
    await query.answer()

    goal_id = int(query.data.split("_")[3])
    user_id = query.from_user.id
    storage = get_async_storage()

    await storage.delete_goal(user_id, goal_id)

    await query.edit_message_text("🗑️ Цель удалена.")


async def show_spreadsheet_link(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show link to Google Spreadsheet."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    storage = get_async_storage()

    url = await storage.get_spreadsheet_url(user_id)

    keyboard = [[InlineKeyboardButton("📊 Открыть таблицу", url=url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📊 Ваша таблица целей готова!\n\n"
        "Нажмите кнопку ниже, чтобы открыть её в браузере.",
        reply_markup=reply_markup,
    )


async def cancel_conversation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancel any conversation."""
    await update.message.reply_text("❌ Операция отменена.")
    return ConversationHandler.END


# Create conversation handler for adding goals
add_goal_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_goal_start, pattern="^add_goal$")],
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
