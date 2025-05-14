from __future__ import annotations

import re
from datetime import timedelta, datetime
from typing import Final, cast, Any, Dict

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
from core.metrics import USER_COMMANDS_TOTAL

# Состояния ConversationHandler
TEXT_GOAL: Final = 0
DEADLINE: Final = 1
AVAILABLE_TIME: Final = 2


# ------------------------------
# Валидация пользовательского ввода
# ------------------------------


def _validate_deadline(text: str):
    """Validates that the user-provided deadline string is within 90 days.

    Supports numeric ("30 days") and Russian word-based numbers ("один месяц").
    If no explicit number is found for units like 'week' or 'month', it assumes 1.

    Args:
        text: The user-input string for the deadline.

    Returns:
        True if the deadline is valid (<= 90 days), False otherwise.
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
            if re.search(rf"\b{w}\b", txt):
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
    """Sends a message asking the user for the goal deadline."""
    assert update.message is not None
    await update.message.reply_text(
        "За какой срок вы планируете достичь цели (например, 'за 2 месяца', 'за 6 недель', 'за 50 дней')? Укажите срок до 3 месяцев."
    )


async def _ask_available_time(update: Update):
    """Sends a message asking the user for their daily time commitment."""
    assert update.message is not None
    await update.message.reply_text(
        "Сколько примерно времени вы готовы уделять достижению цели ежедневно (например, '30 минут', '1-2 часа')?"
    )


# ------------------------------
# Функция построения ConversationHandler
# ------------------------------


def build_setgoal_conv(goal_manager: GoalManager) -> ConversationHandler:
    """Builds the ConversationHandler for the /setgoal command flow.

    Args:
        goal_manager: Instance of GoalManager to process the new goal.

    Returns:
        A ConversationHandler instance for PTB.
    """

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        USER_COMMANDS_TOTAL.labels(command_name="/setgoal").inc()
        assert update.message is not None
        await update.message.reply_text(
            "Какую цель вы хотите достичь? Опишите её как можно подробнее."
        )
        return TEXT_GOAL

    async def input_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.message is not None
        text_raw = update.message.text or ""
        text = text_raw.strip()
        if len(text) < 10:
            await update.message.reply_text(
                "Пожалуйста, опишите цель подробнее (минимум 10 символов)."
            )
            return TEXT_GOAL
        data_dict = cast(Dict[str, Any], context.user_data)
        data_dict["goal_text"] = text
        await _ask_deadline(update)
        return DEADLINE

    async def input_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.message is not None
        text_raw = update.message.text or ""
        text = text_raw.strip()
        # Пытаемся распарсить срок и убедиться, что он не превышает 90 дней
        try:
            days = parse_period(text)
            if days > 90:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "Некорректный срок. Попробуйте ещё раз и убедитесь, что срок <= 3 месяцев."
            )
            return DEADLINE

        data_dict = cast(Dict[str, Any], context.user_data)
        data_dict["deadline"] = text
        await _ask_available_time(update)
        return AVAILABLE_TIME

    async def input_available_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.message is not None
        text_raw = update.message.text or ""
        text = text_raw.strip()
        data_dict = cast(Dict[str, Any], context.user_data)
        data_dict["available_time"] = text
        await update.message.reply_text(
            "Генерирую для вас персональный план... Это может занять некоторое время."
        )

        data_dict = cast(Dict[str, Any], context.user_data)
        goal_text = data_dict["goal_text"]
        deadline = data_dict["deadline"]
        available_time = data_dict["available_time"]
        assert update.effective_user is not None
        user_id = update.effective_user.id

        try:
            spreadsheet_url = await goal_manager.set_new_goal(
                user_id, goal_text, deadline, available_time
            )
            await update.message.reply_text(
                f"✅ Ваша цель *{goal_text}* установлена! План сохранён. \n"
                f"📄 [Открыть таблицу]({spreadsheet_url})\n\n"
                "Используйте /today, чтобы увидеть задачу на сегодня, и /check для отметки выполнения.",
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        except Exception as e:
            await update.message.reply_text(
                "Произошла ошибка при создании цели. Попробуйте позже."
            )
            raise
        return ConversationHandler.END

    async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.message is not None
        await update.message.reply_text("Операция отменена.")
        return ConversationHandler.END

    return ConversationHandler(
        entry_points=[CommandHandler("setgoal", start)],
        states={
            TEXT_GOAL: [
                MessageHandler(filters.Text() & ~filters.Command(), input_goal)
            ],
            DEADLINE: [
                MessageHandler(filters.Text() & ~filters.Command(), input_deadline)
            ],
            AVAILABLE_TIME: [
                MessageHandler(
                    filters.Text() & ~filters.Command(), input_available_time
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        block=True,
        name="setgoal_conv",
        persistent=False,
    )
