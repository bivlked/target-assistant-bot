"""
Модуль с основной бизнес-логикой Telegram-бота.

Управляет целями, задачами и основным функционалом приложения.
"""
import logging
import datetime
import random
import sys
from typing import List, Dict, Any, Optional, Tuple

import llm
import gsheet
import config
import gspread

# Настройка логирования
logger = logging.getLogger(__name__)

class GoalAssistant:
    """Класс управления целями и задачами пользователя."""
    
    def __init__(self, user_id):
        """Инициализация помощника по целям."""
        self.user_id = user_id
        self.sheets_manager = gsheet.GoogleSheetsManager()
        self.user_spreadsheets = {}  # Словарь: user_id -> (spreadsheet_id, sheet_url)
        self.goals = {}  # Словарь для хранения целей пользователей
        self.available_time = {}  # Словарь для хранения доступного времени
        self.deadlines = {}  # Словарь для хранения сроков
        self.llm_client = llm.LLMClient()  # Создаем клиент для работы с LLM
        logger.info("Инициализирован GoalAssistant")
    
    def get_user_spreadsheet(self, user_id: str) -> Tuple[str, str]:
        """
        Получает ID и URL таблицы пользователя или создаёт новую.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Tuple с id таблицы и url для доступа
        """
        if user_id not in self.user_spreadsheets:
            try:
                # Создаём новую таблицу
                spreadsheet_id, url = self.sheets_manager.create_user_spreadsheet(user_id)
                self.user_spreadsheets[user_id] = (spreadsheet_id, url)
                logger.info(f"Создана новая таблица для пользователя {user_id}")
            except Exception as e:
                logger.error(f"Ошибка при создании таблицы для пользователя {user_id}: {str(e)}")
                raise
        
        return self.user_spreadsheets[user_id]
    
    def set_goal(self, user_id, goal_text, available_time=None, deadline=None):
        """
        Устанавливает цель пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
            goal_text: Текстовое описание цели
            available_time: Доступное ежедневное время (строка, опционально)
            deadline: Срок достижения цели (строка, опционально)
            
        Returns:
            Исходная формулировка цели пользователя
        """
        # Извлекаем параметры цели из текста пользователя
        goal_params = self.llm_client.extract_goal_parameters(goal_text)
        
        # Используем параметры из текста или те, что переданы явно
        available_time = available_time or goal_params.get("available_time", "1 час")
        deadline = deadline or goal_params.get("deadline", "30 дней")
        
        # Сохраняем исходную цель без изменений
        self.goals[user_id] = goal_text
        self.available_time[user_id] = available_time
        self.deadlines[user_id] = deadline
        
        # Получаем доступ к таблице пользователя
        spreadsheet_id, _ = self.get_user_spreadsheet(user_id)
        
        # Добавляем исходную цель в таблицу с заданными параметрами
        self.sheets_manager.add_goal(spreadsheet_id, goal_text, available_time, deadline)
        
        logger.info(f"Установлена цель для пользователя {user_id}: {goal_text} (срок: {deadline}, время: {available_time})")
        
        return goal_text
    
    def generate_daily_tasks(self, user_id):
        """
        Генерирует ежедневные задачи для пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Список задач на день
        """
        if user_id not in self.goals:
            logger.warning(f"Попытка сгенерировать задачи без установленной цели для пользователя {user_id}")
            return []
        
        try:
            # Генерируем задачи с помощью LLM
            goal = self.goals[user_id]
            available_time = self.available_time.get(user_id, "30 минут")
            deadline = self.deadlines.get(user_id, "30 дней")
            
            logger.info(f"Генерируем задачи для цели: '{goal}', время: {available_time}, срок: {deadline}")
            
            tasks = self.llm_client.generate_daily_tasks(goal, available_time, deadline)
            
            # Проверяем, что tasks - это список
            if isinstance(tasks, str):
                logger.warning(f"LLM вернул строку вместо списка задач: {tasks}")
                if tasks.strip():
                    # Если это не пустая строка, пробуем преобразовать её в список с одной задачей
                    tasks = [tasks]
                else:
                    # Если пустая строка, возвращаем пустой список
                    return []
            elif not tasks:
                logger.warning(f"LLM вернул пустой список задач")
                return []
            
            # Получаем доступ к таблице пользователя
            spreadsheet_id, _ = self.get_user_spreadsheet(user_id)
            
            # Добавляем задачи в таблицу
            self.sheets_manager.add_tasks(spreadsheet_id, tasks)
            
            logger.info(f"Сгенерировано {len(tasks)} задач для пользователя {user_id}")
            return tasks
            
        except Exception as e:
            logger.error(f"Ошибка при генерации задач: {str(e)}")
            return []
    
    def get_todays_tasks(self, user_id: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Получает задачи пользователя на сегодня.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Tuple со списком задач и URL таблицы
        """
        # Получаем таблицу пользователя
        spreadsheet_id, url = self.get_user_spreadsheet(user_id)
        
        # Получаем задачи на сегодня
        tasks = self.sheets_manager.get_todays_tasks(spreadsheet_id)
        
        return tasks, url
    
    def update_task_status(self, user_id: str, task_index: int, new_status: str) -> bool:
        """
        Обновляет статус задачи пользователя.
        
        Args:
            user_id: ID пользователя
            task_index: Индекс задачи
            new_status: Новый статус задачи
            
        Returns:
            True, если обновление успешно
        """
        # Получаем таблицу пользователя
        spreadsheet_id, _ = self.get_user_spreadsheet(user_id)
        
        # Обновляем статус задачи
        success = self.sheets_manager.update_task_status(spreadsheet_id, task_index, new_status)
        
        if success:
            logger.info(f"Обновлен статус задачи для пользователя {user_id}, задача {task_index+1}: {new_status}")
        
        return success
    
    def get_random_motivation(self, user_id: str = None) -> str:
        """
        Возвращает мотивационное сообщение.
        
        Args:
            user_id: ID пользователя (опционально)
            
        Returns:
            Строка с мотивационным сообщением
        """
        # Если user_id не указан, возвращаем стандартное сообщение
        if not user_id:
            return random.choice(config.MOTIVATIONAL_MESSAGES)
            
        try:
            # Получаем информацию о цели и прогрессе
            goal, stats, _ = self.get_full_status(user_id)
            
            # Если нет цели, возвращаем стандартное сообщение
            if not goal:
                return random.choice(config.MOTIVATIONAL_MESSAGES)
                
            # Получаем параметры для генерации мотивации
            progress_percent = stats.get('progress_percent', None)
            completed_days = stats.get('completed_days', None)
            total_days = stats.get('total_days', None)
            
            # Генерируем персонализированное сообщение
            return self.llm_client.generate_motivation(goal, progress_percent, completed_days, total_days)
            
        except Exception as e:
            logger.error(f"Ошибка при генерации персонализированного мотивационного сообщения: {e}")
            return random.choice(config.MOTIVATIONAL_MESSAGES)
    
    def get_goal_status(self, user_id: str) -> Tuple[Optional[str], List[Dict[str, Any]], str]:
        """
        Получает текущую цель и задачи на сегодня.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Tuple с текущей целью, списком задач и URL таблицы
        """
        # Получаем таблицу пользователя
        spreadsheet_id, url = self.get_user_spreadsheet(user_id)
        
        # Получаем текущую цель
        goal_data = self.sheets_manager.get_goal(spreadsheet_id)
        
        # Получаем задачи на сегодня
        tasks = self.sheets_manager.get_todays_tasks(spreadsheet_id)
        
        return goal_data.get('goal'), tasks, url
    
    def create_full_goal_plan(self, user_id: str, goal_text: str, available_time: str = None, deadline: str = None) -> bool:
        """
        Создает полный план достижения цели на весь период и сохраняет его в таблице.
        
        Args:
            user_id: ID пользователя
            goal_text: Текст цели
            available_time: Доступное ежедневное время (опционально)
            deadline: Срок достижения цели (опционально)
            
        Returns:
            True, если план успешно создан и сохранен
        """
        # Получаем доступ к таблице пользователя
        spreadsheet_id, _ = self.get_user_spreadsheet(user_id)
        
        # Используем параметры из словарей или те, что переданы явно
        available_time = available_time or self.available_time.get(user_id, "1 час")
        deadline = deadline or self.deadlines.get(user_id, "30 дней")
        
        # Сохраняем исходную цель (без улучшения через LLM)
        self.goals[user_id] = goal_text
        self.available_time[user_id] = available_time
        self.deadlines[user_id] = deadline
        
        # Добавляем исходную цель в таблицу с заданными параметрами
        self.sheets_manager.add_goal(spreadsheet_id, goal_text, available_time, deadline)
        
        logger.info(f"Установлена цель для пользователя {user_id}: {goal_text} (срок: {deadline}, время: {available_time})")
        
        # Генерируем полный план с помощью LLM (здесь можно использовать улучшенную версию для генерации плана)
        plan = self.llm_client.generate_full_plan(goal_text, deadline, available_time)
        
        # Сохраняем план в таблице
        success = self.sheets_manager.add_full_plan(spreadsheet_id, plan, goal_text)
        
        if success:
            logger.info(f"Полный план успешно создан для пользователя {user_id}")
        else:
            logger.error(f"Ошибка при создании полного плана для пользователя {user_id}")
        
        return success
    
    def get_today_plan_tasks(self, user_id: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Получает задачи из плана на сегодня.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Tuple со списком задач и URL таблицы
        """
        # Получаем таблицу пользователя
        spreadsheet_id, url = self.get_user_spreadsheet(user_id)
        
        # Получаем текущую дату
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Получаем задачи на сегодня из плана
        tasks = self.sheets_manager.get_tasks_for_date(spreadsheet_id, today)
        
        # Если задач нет в плане, пробуем получить из стандартной таблицы задач
        if not tasks:
            tasks, _ = self.sheets_manager.get_todays_tasks(spreadsheet_id)
        
        return tasks, url
    
    def update_plan_task_status(self, user_id: str, new_status: str) -> bool:
        """
        Обновляет статус всех задач на сегодня в плане.
        
        Args:
            user_id: ID пользователя
            new_status: Новый статус задач
            
        Returns:
            True, если обновление успешно
        """
        # Получаем таблицу пользователя
        spreadsheet_id, _ = self.get_user_spreadsheet(user_id)
        
        # Получаем текущую дату
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Обновляем статус задач на сегодня
        success = self.sheets_manager.update_plan_task_status(spreadsheet_id, today, 0, new_status)
        
        if success:
            logger.info(f"Обновлен статус задач на сегодня для пользователя {user_id}: {new_status}")
        else:
            logger.warning(f"Не удалось обновить статус задач для пользователя {user_id}")
        
        return success
    
    def get_full_status(self, user_id: str) -> Tuple[str, Dict[str, Any], str]:
        """
        Получает полную статистику по цели, включая прогресс по дням и ближайшие задачи.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Tuple с целью, словарем статистики и URL таблицы
        """
        # Получаем таблицу пользователя
        spreadsheet_id, url = self.get_user_spreadsheet(user_id)
        
        # Получаем текущую цель
        goal_data = self.sheets_manager.get_goal(spreadsheet_id)
        goal = goal_data.get('goal', "")
        deadline = goal_data.get('deadline', "30 дней")
        
        if not goal:
            return None, {}, url
        
        # Получаем данные плана из таблицы
        try:
            # Получаем таблицу пользователя
            spreadsheet = self.sheets_manager.get_user_spreadsheet(spreadsheet_id)
            
            # Проверяем наличие листа "План"
            try:
                worksheet = spreadsheet.worksheet("План")
                plan_data = worksheet.get_all_values()
                
                # Если есть данные плана, обрабатываем их
                if len(plan_data) > 4:  # Учитываем заголовки
                    # Пропускаем первые 4 строки (заголовок, описание и шапка таблицы)
                    plan_rows = plan_data[4:]
                    
                    # Текущая дата для сравнения
                    today = datetime.datetime.now().date()
                    
                    # Готовим статистику
                    total_days = len(plan_rows)
                    completed_days = 0
                    current_day_index = 0
                    upcoming_tasks = []
                    
                    # Проходим по всем дням плана
                    for i, row in enumerate(plan_rows):
                        if len(row) >= 8:  # Должны быть дата, день недели, задачи и статус
                            try:
                                # Получаем дату
                                date_obj = datetime.datetime.strptime(row[0], '%Y-%m-%d').date()
                                
                                # Проверяем статус
                                status = row[7]
                                if status == "Выполнено":
                                    completed_days += 1
                                
                                # Определяем индекс текущего дня
                                if date_obj <= today:
                                    current_day_index = i + 1
                                
                                # Собираем ближайшие задачи (сегодняшние и будущие)
                                if date_obj >= today and len(upcoming_tasks) < 3:
                                    # Берем первую непустую задачу из дня
                                    for j in range(2, 7):
                                        if j < len(row) and row[j].strip():
                                            upcoming_tasks.append({
                                                'date': row[0],
                                                'day': row[1],
                                                'task': row[j]
                                            })
                                            break
                            except (ValueError, IndexError) as e:
                                logger.warning(f"Ошибка при обработке строки плана {i+1}: {e}")
                    
                    # Рассчитываем прогресс в процентах
                    progress_percent = int(completed_days / total_days * 100) if total_days > 0 else 0
                    days_passed = current_day_index
                    days_left = total_days - current_day_index
                    
                    # Формируем итоговую статистику
                    stats = {
                        'total_days': total_days,
                        'completed_days': completed_days,
                        'days_passed': days_passed,
                        'days_left': days_left,
                        'progress_percent': progress_percent,
                        'upcoming_tasks': upcoming_tasks[:3]  # Ограничиваем до 3 задач
                    }
                    
                    return goal, stats, url
                
            except gspread.exceptions.WorksheetNotFound:
                logger.warning(f"Лист 'План' не найден в таблице {spreadsheet_id}")
        
        except Exception as e:
            logger.error(f"Ошибка при получении полной статистики: {e}")
        
        # Если не удалось получить данные из плана, возвращаем базовую информацию
        today_tasks, _ = self.get_today_plan_tasks(user_id)
        stats = {
            'total_days': 0,
            'completed_days': 0,
            'days_passed': 0,
            'days_left': 0,
            'progress_percent': 0,
            'upcoming_tasks': [{'date': datetime.datetime.now().strftime('%Y-%m-%d'), 'day': 'Сегодня', 'task': task['task']} 
                               for task in today_tasks[:3]] if today_tasks else []
        }
        
        return goal, stats, url

    def get_progress_report(self, user_id):
        """
        Получает отчет о прогрессе выполнения цели и задач пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            str: Отчет о прогрессе с анализом и рекомендациями
        """
        self.logger.info(f"Запрос отчета о прогрессе для пользователя {user_id}")
        
        # Проверяем, есть ли установленная цель
        goal_data = self.get_goal(user_id)
        if not goal_data:
            return "У вас пока не установлена цель. Используйте команду /setgoal, чтобы начать."
        
        goal = goal_data.get("goal")
        deadline_str = goal_data.get("deadline")
        available_time = goal_data.get("available_time", "")
        
        # Получаем все задачи из плана
        spreadsheet_id = self.spreadsheet_manager.get_user_spreadsheet(user_id)
        if not spreadsheet_id:
            return "Не удалось найти ваш план задач. Пожалуйста, установите цель заново с помощью команды /setgoal."
        
        try:
            # Получаем все задачи из плана
            tasks = []
            try:
                # Пробуем получить задачи с листа "План"
                plan_sheet = self.spreadsheet_manager.service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id, 
                    range="План!A2:E100"
                ).execute()
                values = plan_sheet.get('values', [])
                
                if values:
                    for row in values:
                        if len(row) >= 3:  # Проверяем, что есть достаточное количество столбцов
                            date = row[0] if len(row) > 0 else ""
                            task = row[1] if len(row) > 1 else ""
                            status = row[2] if len(row) > 2 else ""
                            
                            if date and task:  # Проверяем наличие даты и текста задачи
                                tasks.append({
                                    'date': date,
                                    'text': task,
                                    'status': status
                                })
            except Exception as e:
                self.logger.warning(f"Ошибка при получении задач из листа План: {str(e)}")
                # Если не смогли получить задачи из листа "План", пробуем из основного листа
                today_tasks = self.get_todays_tasks(user_id)
                if today_tasks:
                    for task in today_tasks:
                        tasks.append({
                            'date': 'Сегодня',
                            'text': task,
                            'status': 'Не выполнено'  # По умолчанию статус "Не выполнено"
                        })
            
            if not tasks:
                return "Для вашей цели пока не установлены задачи. Используйте команду /today, чтобы получить список задач на сегодня."
            
            # Разделяем задачи на выполненные и оставшиеся
            completed_tasks = [task for task in tasks if task.get('status', '').lower() in ['выполнено', 'done', 'completed', '+', '✓', '✔']]
            remaining_tasks = [task for task in tasks if task not in completed_tasks]
            
            # Рассчитываем количество дней до дедлайна
            days_remaining = 0
            if deadline_str:
                try:
                    deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                    days_remaining = (deadline_date - datetime.now().date()).days
                    if days_remaining < 0:
                        days_remaining = 0
                except ValueError:
                    self.logger.warning(f"Ошибка при парсинге даты дедлайна: {deadline_str}")
            
            # Генерируем отчет с использованием LLM
            report = self.llm_client.generate_plan_progress_report(
                goal, 
                completed_tasks, 
                remaining_tasks, 
                days_remaining,
                available_time
            )
            
            return report
        
        except Exception as e:
            self.logger.error(f"Ошибка при генерации отчета о прогрессе: {str(e)}", exc_info=True)
            return "Не удалось создать отчет о прогрессе. Пожалуйста, попробуйте позже."

# Функция для демонстрации работы модуля
def demo():
    """Запускает демонстрацию функций модуля core."""
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Демонстрация работы модуля core...")
    assistant = GoalAssistant("demo_user")
    
    # Тестовый пользователь
    user_id = "demo_user"
    
    # Устанавливаем цель
    initial_goal = "Хочу выучить Python за месяц"
    print(f"\n1. Устанавливаем цель: '{initial_goal}'")
    improved_goal = assistant.set_goal(user_id, initial_goal)
    print(f"   Улучшенная цель: {improved_goal}")
    
    # Генерируем задачи
    print("\n2. Генерируем задачи на сегодня:")
    tasks = assistant.generate_daily_tasks(user_id)
    for i, task in enumerate(tasks, 1):
        print(f"   {i}. {task}")
    
    # Проверяем задачи
    print("\n3. Получаем текущие задачи:")
    today_tasks, _ = assistant.get_todays_tasks(user_id)
    for i, task in enumerate(today_tasks, 1):
        print(f"   {i}. {task['task']} - {task['status']}")
    
    # Обновляем статус
    if today_tasks:
        print("\n4. Обновляем статус первой задачи:")
        assistant.update_task_status(user_id, 0, "Выполнено")
        print("   Статус обновлен на 'Выполнено'")
        
        # Проверяем обновление
        updated_tasks, _ = assistant.get_todays_tasks(user_id)
        print("   Проверка обновления:")
        for i, task in enumerate(updated_tasks, 1):
            print(f"   {i}. {task['task']} - {task['status']}")
    
    # Мотивационное сообщение
    print("\n5. Мотивационное сообщение:")
    motivation = assistant.get_random_motivation(user_id)
    print(f"   {motivation}")
    
    print("\nДемонстрация завершена!")

if __name__ == "__main__":
    # Проверяем, есть ли аргумент "demo"
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        print("Запустите с аргументом 'demo' для демонстрации: python core.py demo") 