"""
Модуль для работы с Google Sheets API.

Предоставляет функции для создания, чтения и обновления данных в Google таблицах.
"""
import logging
import datetime
from typing import List, Dict, Any, Optional, Tuple

import gspread
from gspread.exceptions import SpreadsheetNotFound
from google.oauth2.service_account import Credentials
from google.auth.exceptions import GoogleAuthError

import config

# Настройка логирования
logger = logging.getLogger(__name__)

# Области доступа для Google Sheets API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def catch_errors(func):
    """
    Декоратор для обработки ошибок при работе с Google Sheets API.
    
    Args:
        func: Функция для декорирования
        
    Returns:
        Декорированная функция с обработкой ошибок
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SpreadsheetNotFound:
            logger.error(f"Таблица не найдена")
            raise
        except GoogleAuthError as e:
            logger.error(f"Ошибка аутентификации Google: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при работе с Google Sheets: {str(e)}")
            raise
    return wrapper

class GoogleSheetsManager:
    """Класс для работы с Google Sheets."""
    
    def __init__(self):
        """Инициализация менеджера Google Sheets."""
        try:
            # Аутентификация с помощью учетных данных сервисного аккаунта
            credentials = Credentials.from_service_account_file(
                config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
            self.client = gspread.authorize(credentials)
            logger.info("Успешная аутентификация в Google Sheets API")
        except Exception as e:
            logger.error(f"Ошибка при аутентификации в Google Sheets: {str(e)}")
            raise

    def _get_service(self):
        """Получает сервис Google Sheets API."""
        return self.client

    @catch_errors
    def create_user_spreadsheet(self, user_id: str) -> Tuple[str, str]:
        """
        Создает новую таблицу для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Tuple с id таблицы и url для доступа
        """
        sheet_title = f"Цели и задачи - {user_id}"
        spreadsheet = self.client.create(sheet_title)
        
        # Получаем первый лист
        worksheet = spreadsheet.get_worksheet(0)
        # Переименовываем его в "Цель"
        worksheet.update_title("Цель")
        
        # Открываем доступ по ссылке (для просмотра)
        spreadsheet.share(None, perm_type='anyone', role='reader')
        
        # Формирование URL
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}"
        
        logger.info(f"Создана новая таблица для пользователя {user_id}: {spreadsheet.id}")
        
        return spreadsheet.id, spreadsheet_url

    @catch_errors
    def get_user_spreadsheet(self, spreadsheet_id: str) -> gspread.Spreadsheet:
        """
        Получает объект таблицы по ID.
        
        Args:
            spreadsheet_id: ID таблицы
            
        Returns:
            Объект таблицы
        """
        return self.client.open_by_key(spreadsheet_id)
    
    @catch_errors
    def add_goal(self, spreadsheet_id: str, goal: str, available_time: str = "30 минут", deadline: str = "30 дней") -> bool:
        """
        Добавляет цель пользователя в таблицу.
        
        Args:
            spreadsheet_id: ID таблицы
            goal: Текст цели
            available_time: Доступное время на выполнение задач
            deadline: Срок выполнения цели
            
        Returns:
            True, если операция выполнена успешно, иначе False
        """
        try:
            # Получаем таблицу
            spreadsheet = self.get_user_spreadsheet(spreadsheet_id)
            
            # Проверяем, существует ли лист "Цель"
            try:
                worksheet = spreadsheet.worksheet("Цель")
            except Exception:
                # Если лист не существует, создаем его
                worksheet = spreadsheet.add_worksheet("Цель", 100, 20)
            
            # Очищаем лист
            worksheet.clear()
            
            # Добавляем заголовки и данные
            values = [
                ["Параметр", "Значение", "Описание"],
                ["Цель", goal, "Ваша основная цель"],
                ["Время на задачи", available_time, "Сколько времени вы готовы уделять задачам ежедневно"],
                ["Срок выполнения", deadline, "Планируемый срок достижения цели"]
            ]
            
            # Обновляем данные
            worksheet.update("A1:C4", values)
            
            # Форматируем заголовки
            worksheet.format("A1:C1", {
                "textFormat": {"bold": True},
                "horizontalAlignment": "CENTER",
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
            })
            
            logger.info(f"Цель успешно добавлена для таблицы {spreadsheet_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении цели для таблицы {spreadsheet_id}: {e}")
            return False
    
    @catch_errors
    def add_tasks(self, spreadsheet_id: str, tasks: List[str]) -> None:
        """
        Добавляет задачи в таблицу.
        
        Args:
            spreadsheet_id: ID таблицы
            tasks: Список задач
        """
        spreadsheet = self.get_user_spreadsheet(spreadsheet_id)
        worksheet = spreadsheet.worksheet(config.DEFAULT_SHEET_NAME)
        
        # Получаем текущую цель
        goal_cell = worksheet.acell('B2')
        if not goal_cell.value:
            logger.warning("Попытка добавить задачи без установленной цели")
            return
        
        goal = goal_cell.value
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Добавляем задачи
        for task in tasks:
            worksheet.append_row([today, goal, task, "Не выполнено"])
        
        logger.info(f"Добавлены задачи в таблицу {spreadsheet_id}: {len(tasks)} задач")
    
    @catch_errors
    def get_goal(self, spreadsheet_id: str) -> dict:
        """
        Получает текущую цель из таблицы.
        
        Args:
            spreadsheet_id: ID таблицы
            
        Returns:
            Словарь с информацией о цели или None, если цель не найдена
        """
        try:
            spreadsheet = self.get_user_spreadsheet(spreadsheet_id)
            
            # Проверяем наличие листа "Цель"
            try:
                worksheet = spreadsheet.worksheet("Цель")
            except Exception:
                logger.warning(f"Лист 'Цель' не найден в таблице {spreadsheet_id}")
                return {}
            
            # Получаем данные
            values = worksheet.get_all_values()
            
            if len(values) < 2 or len(values[1]) < 2:
                logger.warning(f"Цель не найдена в таблице {spreadsheet_id}")
                return {}
            
            goal_data = {
                'goal': values[1][1] if len(values) > 1 and len(values[1]) > 1 else "",
                'available_time': values[2][1] if len(values) > 2 and len(values[2]) > 1 else "30 минут",
                'deadline': values[3][1] if len(values) > 3 and len(values[3]) > 1 else "30 дней"
            }
            
            return goal_data
            
        except Exception as e:
            logger.error(f"Ошибка при получении цели из таблицы {spreadsheet_id}: {e}")
            return {}
    
    @catch_errors
    def get_todays_tasks(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """
        Получает задачи на сегодня из таблицы.
        
        Args:
            spreadsheet_id: ID таблицы
            
        Returns:
            Список задач с их статусами
        """
        spreadsheet = self.get_user_spreadsheet(spreadsheet_id)
        worksheet = spreadsheet.worksheet(config.DEFAULT_SHEET_NAME)
        
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Получаем все данные
        data = worksheet.get_all_records()
        
        # Фильтруем задачи на сегодня
        tasks = []
        for row in data:
            if row[config.SHEET_COLUMNS[0]] == today and row[config.SHEET_COLUMNS[2]]:
                tasks.append({
                    'task': row[config.SHEET_COLUMNS[2]],
                    'status': row[config.SHEET_COLUMNS[3]]
                })
        
        return tasks
    
    @catch_errors
    def update_task_status(self, spreadsheet_id: str, task_index: int, new_status: str) -> bool:
        """
        Обновляет статус задачи.
        
        Args:
            spreadsheet_id: ID таблицы
            task_index: Индекс задачи
            new_status: Новый статус задачи
            
        Returns:
            True, если обновление успешно
        """
        spreadsheet = self.get_user_spreadsheet(spreadsheet_id)
        worksheet = spreadsheet.worksheet(config.DEFAULT_SHEET_NAME)
        
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Получаем все данные
        data = worksheet.get_all_records()
        
        # Фильтруем задачи на сегодня
        today_tasks = []
        for i, row in enumerate(data):
            if row[config.SHEET_COLUMNS[0]] == today and row[config.SHEET_COLUMNS[2]]:
                today_tasks.append({
                    'task': row[config.SHEET_COLUMNS[2]],
                    'status': row[config.SHEET_COLUMNS[3]],
                    'row_index': i + 2  # +2 потому что индексация в gspread с 1 и есть заголовок
                })
        
        if 0 <= task_index < len(today_tasks):
            row_to_update = today_tasks[task_index]['row_index']
            status_column = chr(ord('A') + len(config.SHEET_COLUMNS) - 1)  # Получаем букву последнего столбца (D)
            cell = f"{status_column}{row_to_update}"
            worksheet.update(cell, new_status)
            logger.info(f"Обновлен статус задачи в таблице {spreadsheet_id}, задача {task_index+1} -> {new_status}")
            return True
        
        logger.warning(f"Попытка обновить несуществующую задачу {task_index+1} в таблице {spreadsheet_id}")
        return False

    def _ensure_sheet_exists(self, service, spreadsheet_id: str, sheet_name: str) -> int:
        """
        Проверяет существование листа в таблице, если его нет - создает.
        
        Args:
            service: Сервис Google Sheets API
            spreadsheet_id: ID таблицы
            sheet_name: Название листа
            
        Returns:
            ID листа
        """
        # Получаем информацию о всех листах
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', [])
        
        # Проверяем существование листа
        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        
        # Если лист не существует, создаем его
        requests = [{
            'addSheet': {
                'properties': {
                    'title': sheet_name
                }
            }
        }]
        
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
        
        return response['replies'][0]['addSheet']['properties']['sheetId']

    def _format_goal_sheet(self, service, spreadsheet_id: str, sheet_id: int) -> None:
        """
        Форматирует лист с целью.
        
        Args:
            service: Сервис Google Sheets API
            spreadsheet_id: ID таблицы
            sheet_id: ID листа
        """
        # Настраиваем ширину столбцов
        requests = [
            {
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 1
                    },
                    'properties': {
                        'pixelSize': 200
                    },
                    'fields': 'pixelSize'
                }
            },
            {
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 1,
                        'endIndex': 2
                    },
                    'properties': {
                        'pixelSize': 300
                    },
                    'fields': 'pixelSize'
                }
            },
            # Форматируем заголовки жирным
            {
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': 3
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {
                                'bold': True,
                                'fontSize': 12
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat'
                }
            },
            # Форматируем цель
            {
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 1,
                        'endRowIndex': 2,
                        'startColumnIndex': 0,
                        'endColumnIndex': 3
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.95,
                                'green': 0.95,
                                'blue': 1.0
                            },
                            'textFormat': {
                                'fontSize': 12
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.backgroundColor,userEnteredFormat.textFormat'
                }
            }
        ]
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()

    @catch_errors
    def add_full_plan(self, spreadsheet_id: str, plan: Dict[str, List[str]], goal: str = None) -> bool:
        """
        Добавляет полный план задач на весь период в таблицу.
        
        Args:
            spreadsheet_id: ID таблицы
            plan: Словарь, где ключи - даты, а значения - списки задач
            goal: Цель, к которой относятся задачи (опционально)
            
        Returns:
            True, если план успешно добавлен
        """
        try:
            spreadsheet = self.get_user_spreadsheet(spreadsheet_id)
            
            # Проверяем/создаем лист "План"
            try:
                worksheet = spreadsheet.worksheet("План")
                # Очищаем существующий лист
                worksheet.clear()
            except gspread.exceptions.WorksheetNotFound:
                # Создаем новый лист, если он не существует
                worksheet = spreadsheet.add_worksheet("План", 1000, 4)
            
            # Получаем текущую цель, если она не передана
            if not goal:
                goal_data = self.get_goal(spreadsheet_id)
                goal = goal_data.get('goal', "")
            
            # Формируем заголовки и описание плана
            headers = ["Дата", "День недели", "Задача", "Статус"]
            
            # Добавляем заголовок и описание
            worksheet.update_cell(1, 1, f"План достижения цели: {goal}")
            worksheet.update_cell(2, 1, "План составлен: " + datetime.datetime.now().strftime('%Y-%m-%d'))
            
            # Добавляем заголовки таблицы
            worksheet.update("A4:D4", [headers])
            
            # Форматируем заголовки
            worksheet.format("A4:D4", {
                "textFormat": {"bold": True},
                "horizontalAlignment": "CENTER",
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
            })
            
            # Сортируем даты
            sorted_dates = sorted(plan.keys())
            
            # Подготавливаем данные для добавления в таблицу
            data = []
            row = 5  # Начинаем с 5-й строки после заголовков
            
            for date in sorted_dates:
                # Получаем день недели
                dt = datetime.datetime.strptime(date, '%Y-%m-%d')
                day_of_week = dt.strftime('%A')  # Английский день недели
                
                # Словарь для преобразования английского дня недели в русский
                days_ru = {
                    'Monday': 'Понедельник',
                    'Tuesday': 'Вторник',
                    'Wednesday': 'Среда',
                    'Thursday': 'Четверг',
                    'Friday': 'Пятница',
                    'Saturday': 'Суббота',
                    'Sunday': 'Воскресенье'
                }
                
                day_of_week_ru = days_ru.get(day_of_week, day_of_week)
                
                # Получаем задачу на день (берем первую, если их несколько)
                tasks = plan[date]
                task = tasks[0] if tasks else "Нет задачи на этот день"
                
                # Добавляем строку с датой, днем недели, задачей и статусом
                row_data = [date, day_of_week_ru, task, "Не выполнено"]
                data.append(row_data)
                
                row += 1
            
            # Обновляем таблицу
            if data:
                worksheet.update(f"A5:D{row}", data)
            
            # Устанавливаем ширину столбцов
            worksheet.columns_auto_resize(1, 4)
            
            logger.info(f"План успешно добавлен в таблицу {spreadsheet_id}, {len(sorted_dates)} дней")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении плана в таблицу {spreadsheet_id}: {e}")
            return False

    @catch_errors
    def get_tasks_for_date(self, spreadsheet_id: str, date: str) -> List[Dict[str, Any]]:
        """
        Получает задачи на указанную дату из плана.
        
        Args:
            spreadsheet_id: ID таблицы
            date: Дата в формате 'YYYY-MM-DD'
            
        Returns:
            Список задач с их статусами
        """
        try:
            spreadsheet = self.get_user_spreadsheet(spreadsheet_id)
            
            # Проверяем наличие листа "План"
            try:
                worksheet = spreadsheet.worksheet("План")
            except gspread.exceptions.WorksheetNotFound:
                logger.warning(f"Лист 'План' не найден в таблице {spreadsheet_id}")
                return []
            
            # Получаем все данные
            data = worksheet.get_all_values()
            
            # Пропускаем первые 4 строки (заголовок, описание и шапка таблицы)
            data = data[4:]
            
            # Ищем строку с указанной датой
            tasks = []
            for row in data:
                if len(row) >= 4 and row[0] == date:
                    # Берем задачу из колонки C (индекс 2)
                    if row[2].strip():
                        tasks.append({
                            'task': row[2],
                            'status': row[3] if len(row) > 3 else "Не выполнено"
                        })
                    break
            
            return tasks
            
        except Exception as e:
            logger.error(f"Ошибка при получении задач на {date} из таблицы {spreadsheet_id}: {e}")
            return []

    @catch_errors
    def update_plan_task_status(self, spreadsheet_id: str, date: str, task_index: int, new_status: str) -> bool:
        """
        Обновляет статус задачи в плане.
        
        Args:
            spreadsheet_id: ID таблицы
            date: Дата в формате 'YYYY-MM-DD'
            task_index: Индекс задачи (всегда 0, т.к. теперь только одна задача в день)
            new_status: Новый статус задачи
            
        Returns:
            True, если обновление успешно
        """
        try:
            spreadsheet = self.get_user_spreadsheet(spreadsheet_id)
            
            # Проверяем наличие листа "План"
            try:
                worksheet = spreadsheet.worksheet("План")
            except gspread.exceptions.WorksheetNotFound:
                logger.warning(f"Лист 'План' не найден в таблице {spreadsheet_id}")
                return False
            
            # Получаем все данные
            data = worksheet.get_all_values()
            
            # Пропускаем первые 4 строки (заголовок, описание и шапка таблицы)
            start_row = 5
            
            # Ищем строку с указанной датой
            row_to_update = None
            for i, row in enumerate(data[start_row-1:], start=start_row):
                if row[0] == date:
                    row_to_update = i
                    break
            
            if row_to_update is None:
                logger.warning(f"Дата {date} не найдена в плане в таблице {spreadsheet_id}")
                return False
            
            # Обновляем статус задачи для всей строки (статус находится в колонке D)
            worksheet.update_cell(row_to_update, 4, new_status)
            
            logger.info(f"Обновлен статус задач на {date} в таблице {spreadsheet_id}: {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса задачи на {date} в таблице {spreadsheet_id}: {e}")
            return False

    def get_plan_tasks(self, spreadsheet_id):
        """
        Получает все задачи из плана пользователя.
        
        Args:
            spreadsheet_id: ID таблицы пользователя
            
        Returns:
            Список словарей с задачами, содержащих 'date', 'text' и 'status'
        """
        try:
            with self.catch_errors():
                sheet = self._ensure_sheet_exists(spreadsheet_id, "План")
                
                # Получаем все значения из листа План
                result = sheet.get_all_records()
                
                tasks = []
                
                # Обрабатываем результаты
                for row in result:
                    if 'Дата' in row and 'Задача' in row and 'Статус' in row:
                        # Пропускаем строки с заголовками или пустыми задачами
                        if row['Задача'] and row['Задача'] != 'Задача':
                            tasks.append({
                                'date': row['Дата'],
                                'text': row['Задача'],
                                'status': row['Статус'] if row['Статус'] else 'Не выполнено'
                            })
                
                return tasks
                
        except Exception as e:
            self.logger.error(f"Ошибка при получении задач из плана: {e}", exc_info=True)
            return []

if __name__ == "__main__":
    # Тестирование модуля
    logging.basicConfig(level=logging.INFO)
    gs = GoogleSheetsManager()
    
    # Создаем тестовую таблицу
    spreadsheet_id, url = gs.create_user_spreadsheet("test_user")
    print(f"Создана тестовая таблица: {url}")
    
    # Добавляем цель
    gs.add_goal(spreadsheet_id, "Похудеть на 5 кг за 2 месяца")
    
    # Добавляем задачи
    tasks = [
        "Заниматься на беговой дорожке 30 минут",
        "Съесть не более 1800 калорий",
        "Выпить 2 литра воды"
    ]
    gs.add_tasks(spreadsheet_id, tasks)
    
    # Получаем задачи на сегодня
    today_tasks = gs.get_todays_tasks(spreadsheet_id)
    print("\nЗадачи на сегодня:")
    for i, task in enumerate(today_tasks):
        print(f"{i+1}. {task['task']} - {task['status']}")
    
    # Обновляем статус первой задачи
    gs.update_task_status(spreadsheet_id, 0, "Выполнено")
    print("\nСтатус первой задачи обновлен на 'Выполнено'") 