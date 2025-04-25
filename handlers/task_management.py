from __future__ import annotations

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
)

from core.goal_manager import GoalManager, STATUS_DONE, STATUS_NOT_DONE, STATUS_PARTIAL

CHOOSING_STATUS = 0


def build_task_handlers(goal_manager: GoalManager):
    async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
        task = goal_manager.get_today_task(update.effective_user.id)
        if task:
            text = (
                f"📅 Задача на сегодня ({task['Date']}, {task['DayOfWeek']}):\n\n"
                f"📝 {task['Task']}\n\nСтатус: {task['Status']}"
            )
        else:
            text = "Сначала установите цель с помощью /setgoal."
        await update.message.reply_text(text)

    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = goal_manager.get_goal_status_details(update.effective_user.id)
        await update.message.reply_text(text)

    # ------------- CHECK -------------

    async def check_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
        task = goal_manager.get_today_task(update.effective_user.id)
        if not task:
            await update.message.reply_text("Не удалось найти задачу на сегодня. Установите цель с помощью /setgoal.")
            return ConversationHandler.END
        if task["Status"] == STATUS_DONE:
            await update.message.reply_text("Отличная работа! Задача на сегодня уже выполнена. ✅")
            return ConversationHandler.END

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Выполнено", callback_data=STATUS_DONE),
                    InlineKeyboardButton("❌ Не выполнено", callback_data=STATUS_NOT_DONE),
                ],
                [InlineKeyboardButton("🤔 Частично", callback_data=STATUS_PARTIAL)],
            ]
        )
        await update.message.reply_text(
            f"Как сегодня прошел день по задаче:\n\n📝 {task['Task']}\n\nОтметьте статус:",
            reply_markup=keyboard,
        )
        return CHOOSING_STATUS

    async def check_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        status = query.data
        goal_manager.update_today_task_status(update.effective_user.id, status)
        await query.edit_message_text("Статус обновлен! 💪")
        return ConversationHandler.END

    async def motivation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = goal_manager.generate_motivation_message(update.effective_user.id)
        await update.message.reply_text(msg)

    check_conv = ConversationHandler(
        entry_points=[CommandHandler("check", check_entry)],
        states={
            CHOOSING_STATUS: [CallbackQueryHandler(check_button)],
        },
        fallbacks=[],
        name="check_conv",
        persistent=False,
    )

    return today, status, motivation, check_conv 