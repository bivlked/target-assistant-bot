from __future__ import annotations

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
)

from core.goal_manager import GoalManager, STATUS_DONE, STATUS_NOT_DONE, STATUS_PARTIAL
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS

CHOOSING_STATUS = 0


def build_task_handlers(goal_manager: GoalManager):
    async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
        task = goal_manager.get_today_task(update.effective_user.id)
        if task:
            text = (
                f"📅 Задача на сегодня ({task[COL_DATE]}, {task[COL_DAYOFWEEK]}):\n\n"
                f"📝 {task[COL_TASK]}\n\nСтатус: {task[COL_STATUS]}"
            )
        else:
            text = "Сначала установите цель с помощью /setgoal."
        await update.message.reply_text(text)

    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        data = goal_manager.get_detailed_status(update.effective_user.id)

        # Если цели ещё нет
        if not data.get("goal"):
            await update.message.reply_text("У вас пока нет цели. Используйте /setgoal, чтобы её установить.")
            return

        # Формируем красивый отчёт
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
                status_emoji = "✅" if status == "Выполнено" else "⬜"
                msg_lines.append(f"{status_emoji} {i}. {date}: {text}")

        # Ссылка на таблицу
        msg_lines.append("")
        msg_lines.append(f"📈 [Открыть таблицу]({data['sheet_url']})")

        await update.message.reply_text("\n".join(msg_lines), parse_mode="Markdown", disable_web_page_preview=True)

    # ------------- CHECK -------------

    async def check_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
        task = goal_manager.get_today_task(update.effective_user.id)
        if not task:
            await update.message.reply_text("Не удалось найти задачу на сегодня. Установите цель с помощью /setgoal.")
            return ConversationHandler.END
        if task[COL_STATUS] == STATUS_DONE:
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
            f"Как сегодня прошел день по задаче:\n\n📝 {task[COL_TASK]}\n\nОтметьте статус:",
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