from __future__ import annotations

import re
from datetime import timedelta, datetime
from typing import Final

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

# Состояния ConversationHandler
TEXT_GOAL: Final = 0
DEADLINE: Final = 1
AVAILABLE_TIME: Final = 2


# ------------------------------
# Валидация пользовательского ввода
# ------------------------------

def _validate_deadline(text: str):
    """Проверка, что пользователь указал срок <= 90 дней.
    Поддерживает как цифры, так и словесные числа ("один", "два" ...).
    При отсутствии явного числа для 'неделя/месяц' предполагается 1.
    """
    txt = text.lower()

    # 1. Пытаемся найти число цифрой
    num_match = re.search(r"(\d+)", txt)
    if num_match:
        num = int(num_match.group(1))
    else:
        # 2. Пытаемся распознать словесные числа
        words_map = {
            "один": 1,
            "одна": 1,
            "два": 2,
            "две": 2,
            "три": 3,
            "четыре": 4,
            "пять": 5,
            "шесть": 6,
            "семь": 7,
            "восемь": 8,
            "девять": 9,
            "десять": 10,
        }
        num = None
        for w, val in words_map.items():
            if re.search(fr"\b{w}\b", txt):
                num = val
                break
        # 3. Если число явно не указано, но есть слово 'месяц/неделя/день' – подразумеваем 1
        if num is None and ("месяц" in txt or "недел" in txt or "день" in txt):
            num = 1

    if num is None:
        return False

    # Определяем единицу измерения
    if "нед" in txt:
        days = num * 7
    elif "месяц" in txt or "мес" in txt:
        days = num * 30
    else:
        # По умолчанию считаем дни
        days = num

    return days <= 90


async def _ask_deadline(update: Update):
    await update.message.reply_text(
        "За какой срок вы планируете достичь цели (например, 'за 2 месяца', 'за 6 недель', 'за 50 дней')? Укажите срок до 3 месяцев."
    )


async def _ask_available_time(update: Update):
    await update.message.reply_text(
        "Сколько примерно времени вы готовы уделять достижению цели ежедневно (например, '30 минут', '1-2 часа')?"
    )


# ------------------------------
# Функция построения ConversationHandler
# ------------------------------

def build_setgoal_conv(goal_manager: GoalManager) -> ConversationHandler:
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Какую цель вы хотите достичь? Опишите её как можно подробнее."
        )
        return TEXT_GOAL

    async def input_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if len(text) < 10:
            await update.message.reply_text("Пожалуйста, опишите цель подробнее (минимум 10 символов).")
            return TEXT_GOAL
        context.user_data["goal_text"] = text
        await _ask_deadline(update)
        return DEADLINE

    async def input_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        # Пытаемся распарсить срок и убедиться, что он не превышает 90 дней
        try:
            days = parse_period(text)
            if days > 90:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Некорректный срок. Попробуйте ещё раз и убедитесь, что срок <= 3 месяцев.")
            return DEADLINE

        context.user_data["deadline"] = text
        await _ask_available_time(update)
        return AVAILABLE_TIME

    async def input_available_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        context.user_data["available_time"] = text
        await update.message.reply_text("Генерирую для вас персональный план... Это может занять некоторое время.")

        goal_text = context.user_data["goal_text"]
        deadline = context.user_data["deadline"]
        available_time = context.user_data["available_time"]
        user_id = update.effective_user.id

        try:
            spreadsheet_url = goal_manager.set_new_goal(user_id, goal_text, deadline, available_time)
            await update.message.reply_text(
                f"✅ Ваша цель *{goal_text}* установлена! План сохранён. \n"
                f"📄 [Открыть таблицу]({spreadsheet_url})\n\n"
                "Используйте /today, чтобы увидеть задачу на сегодня, и /check для отметки выполнения.",
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        except Exception as e:
            await update.message.reply_text("Произошла ошибка при создании цели. Попробуйте позже.")
            raise
        return ConversationHandler.END

    async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Операция отменена.")
        return ConversationHandler.END

    return ConversationHandler(
        entry_points=[CommandHandler("setgoal", start)],
        states={
            TEXT_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_goal)],
            DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_deadline)],
            AVAILABLE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_available_time)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        block=True,
        name="setgoal_conv",
        persistent=False,
    ) 