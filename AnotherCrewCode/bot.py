"""
Модуль Telegram-бота для работы с персональным ассистентом по целям.

Содержит обработчики команд и логику взаимодействия с пользователем.
"""
import logging
import os
import colorlog
import sys
from enum import Enum, auto
from typing import Dict, Any, List, Optional, Union
import datetime
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, ConversationHandler, filters
)

import config
import core
import scheduler
import llm

# Настройка логирования
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
class States(Enum):
    """Состояния диалога с пользователем."""
    WAITING_GOAL = auto()  # Ожидаем ввод цели
    WAITING_CLARIFICATION = auto()  # Ожидаем ответы на уточняющие вопросы
    WAITING_TASK_STATUS = auto()
    SELECTING_TASKS = auto()

# Глобальные объекты
task_scheduler = scheduler.TaskScheduler()
application = None  # Глобальная переменная для хранения приложения

# Словарь для хранения объектов GoalAssistant для каждого пользователя
goal_assistants = {}

# Словарь для хранения временного состояния пользователей
user_states = {}

def get_goal_assistant(user_id: str) -> core.GoalAssistant:
    """Получает или создает объект GoalAssistant для пользователя."""
    if user_id not in goal_assistants:
        goal_assistants[user_id] = core.GoalAssistant(user_id)
    return goal_assistants[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or user_id
    
    logger.info(f"Пользователь {username} ({user_id}) запустил бота")
    
    # Регистрируем пользователя в планировщике
    callbacks = {
        'morning': send_morning_reminder,
        'evening': send_evening_reminder,
        'motivation': send_motivation_message
    }
    task_scheduler.register_user(user_id, callbacks)
    
    # Отправляем приветственное сообщение
    await update.message.reply_text(config.WELCOME_MESSAGE)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    await update.message.reply_text(config.HELP_MESSAGE)

async def setgoal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
    """
    Обработчик команды /setgoal.
    
    Запрашивает у пользователя его цель.
    """
    await update.message.reply_text(
        "Какую цель ты хочешь достичь? Пожалуйста, опиши её подробно. Например:\n\n"
        "\"Хочу сбросить 5 кг веса за 2 месяца\"\n"
        "\"Хочу выучить основы Python за 30 дней\"\n"
        "\"Хочу привести квартиру в порядок до конца недели\""
    )
    return States.WAITING_GOAL

async def process_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает введенную пользователем цель.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
        
    Returns:
        Новое состояние разговора
    """
    user_id = str(update.effective_user.id)
    goal_text = update.message.text.strip()
    
    logger.info(f"Пользователь {user_id} ввел цель: {goal_text}")
    
    # Сохраняем цель в контексте пользователя
    user_states[user_id] = {
        'initial_goal': goal_text,
        'clarifying_questions': [],
        'clarifications': []
    }
    
    try:
        # Создаем клиент LLM
        llm_client = llm.LLMClient()
        
        # Получаем уточняющие вопросы по цели
        clarifying_questions = llm_client.generate_clarifying_questions(goal_text)
        
        # Сохраняем вопросы в контексте пользователя
        user_states[user_id]['clarifying_questions'] = clarifying_questions
        
        await update.message.reply_text(
            f"Спасибо! Чтобы помочь тебе достичь цели эффективнее, мне нужно задать несколько уточняющих вопросов:\n\n"
            f"{clarifying_questions}\n\n"
            f"Пожалуйста, ответь на них в одном сообщении."
        )
        return States.WAITING_CLARIFICATION
    except Exception as e:
        logger.error(f"Ошибка при генерации уточняющих вопросов: {e}")
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке вашей цели. Пожалуйста, попробуйте сформулировать её иначе или повторите попытку позже."
        )
        return ConversationHandler.END

async def process_clarification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает уточнения пользователя и генерирует полный план достижения цели.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
        
    Returns:
        Новое состояние разговора
    """
    user_id = str(update.effective_user.id)
    
    # Проверяем, есть ли данные пользователя
    if user_id not in user_states or 'initial_goal' not in user_states[user_id]:
        await update.message.reply_text(
            "Извините, произошла ошибка. Пожалуйста, начните заново с команды /setgoal."
        )
        return ConversationHandler.END
    
    # Получаем ответы пользователя на уточняющие вопросы
    clarification_text = update.message.text.strip()
    initial_goal = user_states[user_id]['initial_goal']
    questions = user_states[user_id]['clarifying_questions']
    
    await update.message.reply_text(
        "Спасибо за ваши уточнения! Обрабатываю информацию и формирую план достижения цели..."
    )
    
    try:
        # Сохраняем уточнения пользователя
        user_states[user_id]['clarifications'] = clarification_text
        
        # Создаем клиент LLM
        llm_client = llm.LLMClient()
        
        # Собираем все входные данные для LLM
        combined_input = f"Исходная цель: {initial_goal}\n\nУточняющие вопросы: {questions}\n\nОтветы пользователя: {clarification_text}"
        goal_params = llm_client.extract_goal_parameters(combined_input)
        
        # Генерируем улучшенную цель
        improved_goal = llm_client.improve_goal(
            goal_text=initial_goal,
            questions=questions,
            answers=clarification_text
        )
        
        # Получаем объект GoalAssistant для пользователя
        goal_assistant = get_goal_assistant(user_id)
        
        # Устанавливаем улучшенную цель с параметрами
        available_time = goal_params.get('available_time')
        deadline = goal_params.get('deadline')
        goal_assistant.set_goal(user_id, improved_goal, available_time, deadline)
        
        # Создаем полный план достижения цели
        success = goal_assistant.create_full_goal_plan(user_id, improved_goal, available_time, deadline)
        
        # Получаем URL таблицы
        spreadsheet_id, url = goal_assistant.get_user_spreadsheet(user_id)
        
        # Сбрасываем временные данные
        user_states[user_id].pop('clarifications', None)
        user_states[user_id].pop('clarifying_questions', None)
        
        # Отправляем сообщение с улучшенной целью и ссылкой на план
        response_message = (
            f"Спасибо за уточнения! Вот улучшенная формулировка твоей цели:\n\n"
            f"*{improved_goal}*\n\n"
        )
        
        if success:
            response_message += (
                f"Я создал для тебя полный план достижения цели! "
                f"Ты можешь просмотреть его [здесь]({url}).\n\n"
                f"Используй команду /today, чтобы увидеть задачи на сегодня."
            )
        else:
            response_message += "Не удалось создать полный план. Пожалуйста, попробуй еще раз или свяжись с поддержкой."
        
        await update.message.reply_text(
            response_message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка при обработке уточнений: {e}")
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке ваших уточнений. Пожалуйста, попробуйте еще раз позже с командой /setgoal."
        )
        return ConversationHandler.END

async def today_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает задачи пользователя на сегодня."""
    user_id = str(update.effective_user.id)
    
    try:
        goal_assistant = get_goal_assistant(user_id)
        
        # Проверяем, есть ли у пользователя установленная цель
        goal_data = goal_assistant.get_goal_status(user_id)
        current_goal = goal_data[0] if goal_data and len(goal_data) > 0 else None
        
        if not current_goal:
            await update.message.reply_text(
                "У тебя пока нет активной цели. Используй команду /setgoal, чтобы установить цель."
            )
            return
        
        # Получаем задачи на сегодня из плана
        tasks, sheet_url = goal_assistant.get_today_plan_tasks(user_id)
        
        if not tasks:
            # Если задач нет в плане, генерируем новые задачи
            goal_assistant.generate_daily_tasks(user_id)
            tasks, sheet_url = goal_assistant.get_todays_tasks(user_id)
        
        if not tasks:
            await update.message.reply_text(
                "На сегодня у тебя нет запланированных задач. Возможно, пора обновить цель или план."
            )
            return
        
        # Форматируем сообщение с задачами
        tasks_message = f"Твои задачи на сегодня по цели: *{current_goal}*\n\n"
        
        # Добавляем задачи в сообщение
        for i, task in enumerate(tasks, 1):
            if isinstance(task, dict) and "task" in task:
                task_text = task["task"]
                status = task.get("status", "")
                status_emoji = "✅" if status.lower() == "выполнено" else "⬜"
                tasks_message += f"{status_emoji} {task_text}\n"
            else:
                tasks_message += f"⬜ {task}\n"
        
        # Добавляем ссылку на таблицу, если есть
        if sheet_url:
            tasks_message += f"\n[Посмотреть полный план]({sheet_url})"
        
        await update.message.reply_text(
            tasks_message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    
    except Exception as e:
        logger.error(f"Ошибка при получении задач: {e}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при получении задач. Пожалуйста, попробуй позже или установи новую цель с помощью /setgoal."
        )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /status."""
    user_id = str(update.effective_user.id)
    
    try:
        # Получаем ассистента для пользователя
        goal_assistant = get_goal_assistant(user_id)
        
        # Получаем полную статистику по цели
        goal, stats, sheet_url = goal_assistant.get_full_status(user_id)
        
        if not goal:
            await update.message.reply_text(
                "У тебя еще нет поставленной цели. Используй /setgoal чтобы установить её."
            )
            return
        
        # Формируем сообщение со статусом
        response = f"🎯 Твоя цель: {goal}\n\n"
        
        # Добавляем прогресс
        total_days = stats.get('total_days', 0)
        days_passed = stats.get('days_passed', 0)
        days_left = stats.get('days_left', 0)
        completed_days = stats.get('completed_days', 0)
        progress_percent = stats.get('progress_percent', 0)
        
        if total_days > 0:
            response += f"📊 Прогресс: {progress_percent}% ({completed_days}/{total_days} дней)\n"
            response += f"⏱ Прошло дней: {days_passed}, осталось: {days_left}\n\n"
        
        # Добавляем ближайшие задачи
        upcoming_tasks = stats.get('upcoming_tasks', [])
        if upcoming_tasks:
            response += "📝 Ближайшие задачи:\n"
            for i, task in enumerate(upcoming_tasks, 1):
                date = task.get('date', '')
                day = task.get('day', '')
                task_text = task.get('task', '')
                
                # Форматируем дату для отображения
                try:
                    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                    formatted_date = date_obj.strftime('%d.%m.%Y')
                except ValueError:
                    formatted_date = date
                
                response += f"{i}. {formatted_date} ({day}): {task_text}\n"
        else:
            response += "На ближайшее время задач не запланировано.\n"
        
        # Добавляем ссылку на таблицу
        response += f"\n📈 Подробная статистика: {sheet_url}"
        
        await update.message.reply_text(response)
    
    except Exception as e:
        logger.error(f"Ошибка при получении статуса: {str(e)}")
        await update.message.reply_text(
            "Произошла ошибка при получении статуса. Пожалуйста, попробуй еще раз позже."
        )

async def check_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /check для отметки выполнения задач."""
    user_id = str(update.effective_user.id)
    
    try:
        # Получаем ассистента для пользователя
        goal_assistant = get_goal_assistant(user_id)
        
        # Получаем задачи на сегодня
        tasks, _ = goal_assistant.get_today_plan_tasks(user_id)
        
        if not tasks:
            await update.message.reply_text(
                "На сегодня у вас нет задач. Используйте /today, чтобы получить список задач на сегодня."
            )
            return
        
        # Сохраняем задачи в контексте пользователя
        user_states[user_id] = {
            'tasks': tasks
        }
        
        # Создаем клавиатуру для выбора задач
        keyboard = []
        
        for i, task in enumerate(tasks):
            # Текст кнопки с учетом текущего статуса
            task_text = task.get("task", str(task)) if isinstance(task, dict) else str(task)
            task_status = task.get("status", "Не выполнено") if isinstance(task, dict) else "Не выполнено"
            
            if task_status == "Выполнено":
                button_text = f"✅ {i+1}. {task_text[:30]}..."
            else:
                button_text = f"⏳ {i+1}. {task_text[:30]}..."
            
            # Добавляем кнопку для задачи
            keyboard.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"task_{i}"
            )])
        
        # Добавляем кнопки для групповой отметки
        keyboard.append([
            InlineKeyboardButton("✅ Все выполнены", callback_data="all_done"),
            InlineKeyboardButton("❌ Ничего не выполнено", callback_data="none_done")
        ])
        
        # Добавляем кнопку завершения
        keyboard.append([InlineKeyboardButton("Готово", callback_data="done")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Выберите задачи, которые вы выполнили сегодня:",
            reply_markup=reply_markup
        )
        
        return States.SELECTING_TASKS
    
    except Exception as e:
        logger.error(f"Ошибка при получении задач для проверки: {e}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при получении списка задач. Пожалуйста, попробуйте позже."
        )
        return None

async def motivation_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /motivation."""
    user_id = str(update.effective_user.id)
    
    # Получаем ассистента для пользователя
    goal_assistant = get_goal_assistant(user_id)
    
    # Получаем персонализированное мотивационное сообщение
    message = goal_assistant.get_random_motivation(user_id)
    
    await update.message.reply_text(f"💪 {message}")

async def evening_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[States]:
    """
    Обработчик команды /evening.
    
    Позволяет пользователю отчитаться о выполнении задач на сегодня.
    """
    user_id = str(update.effective_user.id)
    
    try:
        # Получаем ассистента для пользователя
        goal_assistant = get_goal_assistant(user_id)
        
        # Получаем задачи на сегодня
        tasks, _ = goal_assistant.get_today_plan_tasks(user_id)
        
        if not tasks:
            await update.message.reply_text(
                "У вас нет задач на сегодня. Используйте /today чтобы увидеть или создать задачи."
            )
            return None
        
        # Сохраняем задачи в контексте пользователя
        user_states[user_id] = {
            'tasks': tasks
        }
        
        # Создаем клавиатуру для выбора задач
        keyboard = []
        
        for i, task in enumerate(tasks):
            # Текст кнопки с учетом текущего статуса
            task_text = task["task"] if isinstance(task, dict) and "task" in task else str(task)
            task_status = task["status"] if isinstance(task, dict) and "status" in task else "Не выполнено"
            
            if task_status == "Выполнено":
                button_text = f"✅ {i+1}. {task_text[:30]}..."
            else:
                button_text = f"⏳ {i+1}. {task_text[:30]}..."
            
            # Добавляем кнопку для задачи
            keyboard.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"task_{i}"
            )])
        
        # Добавляем кнопки для группового отметки
        keyboard.append([
            InlineKeyboardButton("✅ Все выполнены", callback_data="all_done"),
            InlineKeyboardButton("❌ Ничего не выполнено", callback_data="none_done")
        ])
        
        # Добавляем кнопку завершения
        keyboard.append([InlineKeyboardButton("Готово", callback_data="done")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Выберите задачи, которые вы выполнили сегодня:",
            reply_markup=reply_markup
        )
        
        return States.SELECTING_TASKS
    
    except Exception as e:
        logger.error(f"Ошибка при создании вечернего отчета: {str(e)}")
        await update.message.reply_text(
            "Произошла ошибка при создании отчета. Пожалуйста, попробуйте еще раз позже."
        )
        return None

async def task_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[States]:
    """Обрабатывает выбор задач пользователем."""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    data = query.data
    
    # Если пользователь нажал "Готово"
    if data == "done":
        # Формируем итоговое сообщение
        tasks = user_states[user_id]['tasks']
        completed_tasks = len([t for t in tasks if isinstance(t, dict) and t.get("status") == "Выполнено"])
        total_tasks = len(tasks)
        
        # Обновляем статус задач в плане
        goal_assistant = get_goal_assistant(user_id)
        if completed_tasks == total_tasks:
            goal_assistant.update_plan_task_status(user_id, "Выполнено")
        elif completed_tasks > 0:
            goal_assistant.update_plan_task_status(user_id, "Частично выполнено")
        else:
            goal_assistant.update_plan_task_status(user_id, "Не выполнено")
        
        response = f"Отлично! Вы выполнили {completed_tasks} из {total_tasks} задач сегодня.\n\n"
        
        # Добавляем мотивационное сообщение
        if completed_tasks == total_tasks:
            response += "🏆 Поздравляю с выполнением всех задач! Продолжайте в том же духе!"
        elif completed_tasks > 0:
            response += "👍 Хороший прогресс! Завтра будет еще лучше!"
        else:
            response += "Не расстраивайтесь, если сегодня не получилось выполнить задачи. Завтра новый день и новые возможности!"
        
        await query.edit_message_text(response)
        
        # Очищаем состояние пользователя
        if user_id in user_states:
            del user_states[user_id]
        
        return ConversationHandler.END
    
    # Если пользователь выбрал "Все выполнены"
    elif data == "all_done":
        tasks = user_states[user_id]['tasks']
        for i in range(len(tasks)):
            if isinstance(tasks[i], dict):
                tasks[i]["status"] = "Выполнено"
            else:
                tasks[i] = {"task": str(tasks[i]), "status": "Выполнено"}
        
        # Обновляем клавиатуру
        keyboard = []
        
        for i, task in enumerate(tasks):
            task_text = task["task"] if isinstance(task, dict) and "task" in task else str(task)
            button_text = f"✅ {i+1}. {task_text[:30]}..."
            
            keyboard.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"task_{i}"
            )])
        
        # Добавляем кнопки для группового отметки
        keyboard.append([
            InlineKeyboardButton("✅ Все выполнены", callback_data="all_done"),
            InlineKeyboardButton("❌ Ничего не выполнено", callback_data="none_done")
        ])
        
        keyboard.append([InlineKeyboardButton("Готово", callback_data="done")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Выберите задачи, которые вы выполнили сегодня:",
            reply_markup=reply_markup
        )
        
        return States.SELECTING_TASKS
    
    # Если пользователь выбрал "Ничего не выполнено"
    elif data == "none_done":
        tasks = user_states[user_id]['tasks']
        for i in range(len(tasks)):
            if isinstance(tasks[i], dict):
                tasks[i]["status"] = "Не выполнено"
            else:
                tasks[i] = {"task": str(tasks[i]), "status": "Не выполнено"}
        
        # Обновляем клавиатуру
        keyboard = []
        
        for i, task in enumerate(tasks):
            task_text = task["task"] if isinstance(task, dict) and "task" in task else str(task)
            button_text = f"⏳ {i+1}. {task_text[:30]}..."
            
            keyboard.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"task_{i}"
            )])
        
        # Добавляем кнопки для группового отметки
        keyboard.append([
            InlineKeyboardButton("✅ Все выполнены", callback_data="all_done"),
            InlineKeyboardButton("❌ Ничего не выполнено", callback_data="none_done")
        ])
        
        keyboard.append([InlineKeyboardButton("Готово", callback_data="done")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Выберите задачи, которые вы выполнили сегодня:",
            reply_markup=reply_markup
        )
        
        return States.SELECTING_TASKS
        
    # Если пользователь выбрал задачу
    elif data.startswith("task_"):
        task_index = int(data.split("_")[1])
        
        try:
            # Получаем текущие задачи
            tasks = user_states[user_id]['tasks']
            
            if 0 <= task_index < len(tasks):
                # Проверяем формат задачи
                if not isinstance(tasks[task_index], dict) or "status" not in tasks[task_index]:
                    # Если задача имеет неправильный формат, преобразуем её
                    task_text = str(tasks[task_index]) if not isinstance(tasks[task_index], dict) else tasks[task_index].get("task", "")
                    tasks[task_index] = {"task": task_text, "status": "Не выполнено"}
                
                # Меняем статус задачи на противоположный
                current_status = tasks[task_index]["status"]
                new_status = "Не выполнено" if current_status == "Выполнено" else "Выполнено"
                
                # Обновляем статус в локальном кеше
                tasks[task_index]["status"] = new_status
                
                # Обновляем клавиатуру
                keyboard = []
                
                for i, task in enumerate(tasks):
                    # Извлекаем текст и статус задачи
                    task_text = task["task"] if isinstance(task, dict) and "task" in task else str(task)
                    task_status = task["status"] if isinstance(task, dict) and "status" in task else "Не выполнено"
                    
                    if task_status == "Выполнено":
                        button_text = f"✅ {i+1}. {task_text[:30]}..."
                    else:
                        button_text = f"⏳ {i+1}. {task_text[:30]}..."
                    
                    keyboard.append([InlineKeyboardButton(
                        button_text, 
                        callback_data=f"task_{i}"
                    )])
                
                # Добавляем кнопки для группового отметки
                keyboard.append([
                    InlineKeyboardButton("✅ Все выполнены", callback_data="all_done"),
                    InlineKeyboardButton("❌ Ничего не выполнено", callback_data="none_done")
                ])
                
                keyboard.append([InlineKeyboardButton("Готово", callback_data="done")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "Выберите задачи, которые вы выполнили сегодня:",
                    reply_markup=reply_markup
                )
                
                return States.SELECTING_TASKS
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса задачи: {str(e)}")
            await query.edit_message_text(
                "Произошла ошибка при обновлении статуса задачи. Пожалуйста, попробуйте еще раз позже."
            )
            return ConversationHandler.END
    
    return None

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущий диалог."""
    user_id = str(update.effective_user.id)
    
    # Очищаем состояние пользователя
    if user_id in user_states:
        del user_states[user_id]
    
    await update.message.reply_text("Операция отменена.")
    
    return ConversationHandler.END

# Функции для планировщика
async def send_morning_reminder(user_id: str) -> None:
    """
    Отправляет утреннее напоминание пользователю.
    
    Args:
        user_id: ID пользователя
    """
    try:
        # Получаем бота из приложения
        bot = application.bot
        
        # Получаем ассистента для пользователя
        goal_assistant = get_goal_assistant(user_id)
        
        # Получаем сегодняшние задачи из плана
        tasks, sheet_url = goal_assistant.get_today_plan_tasks(user_id)
        
        # Если в плане нет задач, проверяем наличие цели
        if not tasks:
            # Получаем информацию о цели
            goal, _, _ = goal_assistant.get_goal_status(user_id)
            
            if not goal:
                # Если нет цели, отправляем предложение установить
                await bot.send_message(
                    chat_id=user_id,
                    text="Доброе утро! У вас пока нет поставленной цели. Используйте /setgoal чтобы задать цель и получить план действий."
                )
                return
            
            # Если есть цель, но нет задач на сегодня, генерируем их
            tasks = goal_assistant.generate_daily_tasks(user_id)
            
            if not tasks:
                await bot.send_message(
                    chat_id=user_id,
                    text="Доброе утро! К сожалению, не удалось найти или сгенерировать задачи на сегодня. Пожалуйста, используйте /today для создания задач вручную."
                )
                return
        
        # Получаем текущую дату
        today = datetime.datetime.now()
        date_str = today.strftime('%Y-%m-%d')
        day_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"][today.weekday()]
        
        # Формируем сообщение
        message = f"Доброе утро! Ваши задачи на сегодня ({date_str}, {day_of_week}):\n\n"
        
        for i, task in enumerate(tasks, 1):
            if isinstance(task, dict) and "task" in task:
                message += f"{i}. {task['task']}\n"
            else:
                message += f"{i}. {task}\n"
        
        # Добавляем мотивационное сообщение
        motivation = goal_assistant.get_random_motivation(user_id)
        message += f"\n{motivation} 💪"
        
        # Добавляем ссылку на план, если она есть
        if sheet_url:
            message += f"\n\nПолный план доступен по ссылке: {sheet_url}"
        
        # Отправляем сообщение
        await bot.send_message(chat_id=user_id, text=message)
        
    except Exception as e:
        logger.error(f"Ошибка при отправке утреннего напоминания пользователю {user_id}: {str(e)}")

async def send_evening_reminder(user_id: str) -> None:
    """
    Отправляет вечерний опрос пользователю.
    
    Args:
        user_id: ID пользователя
    """
    try:
        # Получаем бота из приложения
        bot = application.bot
        
        # Получаем ассистента для пользователя
        goal_assistant = get_goal_assistant(user_id)
        
        # Получаем задачи на сегодня
        tasks, _ = goal_assistant.get_todays_tasks(user_id)
        
        if not tasks:
            # Если нет задач, просто отправляем напоминание
            await bot.send_message(
                chat_id=user_id,
                text="Вечер добрый! Не забудь поставить цели на завтра с помощью /setgoal."
            )
            return
        
        # Отправляем напоминание об отчете
        await bot.send_message(
            chat_id=user_id,
            text="Вечер добрый! Не забудь отметить выполненные сегодня задачи с помощью /evening."
        )
        
    except Exception as e:
        logger.error(f"Ошибка при отправке вечернего напоминания пользователю {user_id}: {str(e)}")

async def send_motivation_message(user_id: str) -> None:
    """
    Отправляет мотивационное сообщение пользователю.
    
    Args:
        user_id: ID пользователя
    """
    try:
        # Получаем бота из приложения
        bot = application.bot
        
        # Получаем ассистента для пользователя
        goal_assistant = get_goal_assistant(user_id)
        
        # Получаем персонализированное мотивационное сообщение
        message = goal_assistant.get_random_motivation(user_id)
        
        # Отправляем сообщение
        await bot.send_message(
            chat_id=user_id,
            text=f"💪 {message}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при отправке мотивационного сообщения пользователю {user_id}: {str(e)}")

# Обработчик мотивации
async def get_motivation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет пользователю мотивационное сообщение."""
    user_id = str(update.effective_user.id)
    
    try:
        goal_assistant = get_goal_assistant(user_id)
        
        # Получаем полную статистику по цели
        goal, stats, _ = goal_assistant.get_full_status(user_id)
        
        if goal:
            # Получаем персонализированную мотивацию по цели 
            progress_percent = stats.get('progress_percent', None)
            completed_days = stats.get('completed_days', None)
            total_days = stats.get('total_days', None)
            
            motivation = goal_assistant.get_random_motivation(user_id)
            
            await update.message.reply_text(
                f"💪 {motivation}",
                parse_mode='Markdown'
            )
        else:
            # Если цели нет, используем стандартную мотивацию
            motivation = random.choice(config.MOTIVATIONAL_MESSAGES)
            await update.message.reply_text(
                f"💪 {motivation}",
                parse_mode='Markdown'
            )
    
    except Exception as e:
        logger.error(f"Ошибка при отправке мотивации: {e}", exc_info=True)
        # Используем резервный вариант из конфига
        motivation = random.choice(config.MOTIVATIONAL_MESSAGES)
        await update.message.reply_text(
            f"💪 {motivation}",
            parse_mode='Markdown'
        )

async def progress_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Генерирует и отправляет отчет о прогрессе выполнения плана.
    
    Отчет включает:
    - Статистику по выполненным и оставшимся задачам
    - Оценку прогресса относительно дедлайна
    - Рекомендации для улучшения результатов
    """
    user_id = str(update.effective_user.id)
    logger.info(f"Пользователь {user_id} запросил отчет о прогрессе")
    
    # Получаем отчет из GoalAssistant
    goal_assistant = get_goal_assistant(user_id)
    progress_text = goal_assistant.get_progress_report(user_id)
    
    # Отправляем отчет пользователю
    await update.message.reply_text(
        progress_text,
        parse_mode="HTML"
    )
    
    # Добавляем клавиатуру с полезными командами после отчета
    keyboard = [
        [InlineKeyboardButton("Задачи на сегодня", callback_data="today_tasks")],
        [InlineKeyboardButton("Мотивация", callback_data="motivation")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Что хотите сделать дальше?",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает нажатия на кнопки в интерактивных сообщениях.
    """
    query = update.callback_query
    await query.answer()  # Отвечаем на запрос, чтобы убрать часы загрузки
    
    user_id = str(update.effective_user.id)
    callback_data = query.data
    
    # Обработка кнопок из отчета о прогрессе
    if callback_data == "today_tasks":
        # Отправляем список задач на сегодня
        goal_assistant = get_goal_assistant(user_id)
        tasks, sheet_url = goal_assistant.get_today_plan_tasks(user_id)
        
        if not tasks:
            await query.message.reply_text(
                "На сегодня у вас нет запланированных задач. "
                "Используйте /setgoal, чтобы установить цель и получить задачи."
            )
            return
        
        # Формируем сообщение со списком задач
        message = "📋 Задачи на сегодня:\n\n"
        
        for i, task in enumerate(tasks, 1):
            status = "✅" if task.get("status") == "Выполнено" else "⏳"
            task_text = task.get("task", task) if isinstance(task, dict) else task
            message += f"{i}. {status} {task_text}\n"
        
        message += f"\n📊 Подробный план: {sheet_url}"
        
        await query.message.reply_text(message)
        
    elif callback_data == "motivation":
        # Отправляем мотивационное сообщение
        goal_assistant = get_goal_assistant(user_id)
        message = goal_assistant.get_random_motivation(user_id)
        await query.message.reply_text(f"💪 {message}")
    
    # Другие обработчики callback_data...

def setup_logging():
    """Настраивает систему логирования."""
    # Создаем обработчик для файла
    file_handler = logging.FileHandler(config.LOG_FILE)
    file_handler.setLevel(config.LOG_LEVEL_FILE)
    file_formatter = logging.Formatter(config.LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    
    # Создаем обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.LOG_LEVEL_CONSOLE)
    console_formatter = logging.Formatter(config.LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

def main():
    """Запускает бота."""
    global application  # Объявляем, что используем глобальную переменную
    
    # Создаем экземпляр приложения
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # Настраиваем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("setgoal", setgoal))
    application.add_handler(CommandHandler("today", today_tasks))
    application.add_handler(CommandHandler("check", check_tasks))
    application.add_handler(CommandHandler("motivation", motivation_message))
    application.add_handler(CommandHandler("progress", progress_report))  # Обработчик отчета о прогрессе

    # Настраиваем обработчики обратных вызовов (callback)
    application.add_handler(CallbackQueryHandler(button_callback))

    # Настраиваем диалоговые состояния (ConversationHandler)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("setgoal", setgoal)],
        states={
            States.WAITING_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_goal)],
            States.WAITING_CLARIFICATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_clarification)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(conv_handler)

    # Настраиваем обработчики команды evening с выбором задач
    evening_handler = ConversationHandler(
        entry_points=[CommandHandler("evening", evening_report)],
        states={
            States.SELECTING_TASKS: [CallbackQueryHandler(task_selection, pattern=r"^(task_\d+|all_done|none_done|done)$")]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True
    )
    application.add_handler(evening_handler)
    
    # Запускаем планировщик
    task_scheduler.schedule_all_tasks()
    task_scheduler.start()
    
    # Запускаем бота
    application.run_polling()
    
    # При выходе останавливаем планировщик
    task_scheduler.shutdown()

if __name__ == "__main__":
    main() 