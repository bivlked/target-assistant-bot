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
    STATUS_DONE,
    STATUS_NOT_DONE,
    STATUS_PARTIAL,
)
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS
from utils.helpers import format_date

CHOOSING_STATUS = 0


def build_task_handlers(goal_manager: GoalManager):
    async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):  # noqa: D401
        task = await goal_manager.get_today_task_async(update.effective_user.id)
        if task:
            text = (
                f"📅 Задача на сегодня ({task[COL_DATE]}, {task[COL_DAYOFWEEK]}):\n\n"
                f"📝 {task[COL_TASK]}\n\nСтатус: {task[COL_STATUS]}"
            )
        else:
            text = "У вас пока нет целей. Установите её с помощью /setgoal."
        await update.message.reply_text(text)

    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):  # noqa: D401
        data = await goal_manager.get_detailed_status_async(update.effective_user.id)

        # Нет данных о цели или план пустой
        if not data.get("goal") or data.get("total_days", 0) == 0:
            await update.message.reply_text(
                "У вас пока нет цели или план ещё не создан. Используйте /setgoal, чтобы начать."
            )
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

        await update.message.reply_text(
            "\n".join(msg_lines), parse_mode="Markdown", disable_web_page_preview=True
        )

    # ------------- CHECK -------------

    async def check_entry(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ):  # noqa: D401
        task = await goal_manager.get_today_task_async(update.effective_user.id)
        if not task:
            await update.message.reply_text(
                "У вас пока нет цели или задач на сегодня. Сначала выполните /setgoal."
            )
            return ConversationHandler.END
        if task[COL_STATUS] == STATUS_DONE:
            await update.message.reply_text(
                "Отличная работа! Задача на сегодня уже выполнена. ✅"
            )
            return ConversationHandler.END

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Выполнено", callback_data=STATUS_DONE),
                    InlineKeyboardButton(
                        "❌ Не выполнено", callback_data=STATUS_NOT_DONE
                    ),
                ],
                [InlineKeyboardButton("🤔 Частично", callback_data=STATUS_PARTIAL)],
            ]
        )
        await update.message.reply_text(
            f"Как сегодня прошел день по задаче:\n\n📝 {task[COL_TASK]}\n\nОтметьте статус:",
            reply_markup=keyboard,
        )
        return CHOOSING_STATUS

    async def check_button(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ):  # noqa: D401
        query = update.callback_query
        await query.answer()
        status_val = query.data
        await goal_manager.batch_update_task_statuses_async(
            update.effective_user.id,
            {format_date(datetime.now()): status_val},
        )
        await query.edit_message_text("Статус обновлен! 💪")
        return ConversationHandler.END

    async def motivation(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ):  # noqa: D401
        msg = await goal_manager.generate_motivation_message_async(
            update.effective_user.id
        )
        await update.message.reply_text(msg)

    check_conv = ConversationHandler(
        entry_points=[CommandHandler("check", check_entry)],
        states={CHOOSING_STATUS: [CallbackQueryHandler(check_button)]},
        fallbacks=[],
        name="check_conv",
        persistent=False,
    )

    return today, status, motivation, check_conv
