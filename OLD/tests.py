"""
Модуль тестирования для персонального ассистента по целям.

Содержит тесты с использованием pytest и моков для внешних зависимостей.
"""
import datetime
import random
import pytest
from unittest.mock import patch, MagicMock, call

import config
import core
import gsheet
import llm

# Mock-данные для тестов
MOCK_USER_ID = "test_user"
MOCK_GOAL = "Похудеть на 5 кг за 2 месяца"
MOCK_IMPROVED_GOAL = "Снизить вес на 5 кг за 2 месяца путем правильного питания и регулярных тренировок"
MOCK_SHEET_ID = "mock_spreadsheet_id"
MOCK_SHEET_URL = "https://docs.google.com/spreadsheets/d/mock_spreadsheet_id"

MOCK_TASKS = [
    "Тренировка кардио 30 минут",
    "Приготовить здоровый обед с высоким содержанием белка",
    "Выпить 2 литра воды"
]

MOCK_TASKS_WITH_STATUS = [
    {"task": "Тренировка кардио 30 минут", "status": "Не выполнено"},
    {"task": "Приготовить здоровый обед с высоким содержанием белка", "status": "Не выполнено"},
    {"task": "Выпить 2 литра воды", "status": "Не выполнено"}
]

# Mock-ответ OpenAI API
MOCK_OPENAI_RESPONSE = MagicMock()
MOCK_OPENAI_RESPONSE.choices = [MagicMock()]
MOCK_OPENAI_RESPONSE.choices[0].message.content = MOCK_IMPROVED_GOAL

class TestLLM:
    """Тесты для модуля llm."""
    
    @patch('openai.OpenAI')
    def test_generate_improved_goal(self, mock_openai):
        """Тест генерации улучшенной цели."""
        # Настраиваем моки
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = MOCK_OPENAI_RESPONSE
        
        # Вызываем тестируемую функцию
        with patch('llm.client', mock_client):
            result = llm.generate_improved_goal(MOCK_GOAL)
        
        # Проверяем результаты
        assert result == MOCK_IMPROVED_GOAL
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('openai.OpenAI')
    def test_generate_daily_tasks(self, mock_openai):
        """Тест генерации ежедневных задач."""
        # Настраиваем моки
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Мокаем ответ с задачами
        task_response = MagicMock()
        task_response.choices = [MagicMock()]
        task_response.choices[0].message.content = "\n".join(MOCK_TASKS)
        mock_client.chat.completions.create.return_value = task_response
        
        # Вызываем тестируемую функцию
        with patch('llm.client', mock_client):
            result = llm.generate_daily_tasks(MOCK_GOAL)
        
        # Проверяем результаты
        assert result == MOCK_TASKS
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('openai.OpenAI')
    def test_llm_error_handling(self, mock_openai):
        """Тест обработки ошибок."""
        # Настраиваем моки
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Проверяем, что ошибка правильно обрабатывается
        with patch('llm.client', mock_client):
            with pytest.raises(Exception):
                llm.generate_improved_goal(MOCK_GOAL)

class TestGoogleSheets:
    """Тесты для модуля gsheet."""
    
    @patch('gspread.authorize')
    @patch('google.oauth2.service_account.Credentials.from_service_account_file')
    def test_create_user_spreadsheet(self, mock_creds, mock_authorize):
        """Тест создания таблицы пользователя."""
        # Настраиваем моки
        mock_client = MagicMock()
        mock_authorize.return_value = mock_client
        
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.id = MOCK_SHEET_ID
        mock_spreadsheet.url = MOCK_SHEET_URL
        mock_client.create.return_value = mock_spreadsheet
        
        mock_worksheet = MagicMock()
        mock_spreadsheet.sheet1 = mock_worksheet
        
        # Создаем объект и вызываем тестируемый метод
        gs = gsheet.GoogleSheetsManager()
        sheet_id, url = gs.create_user_spreadsheet(MOCK_USER_ID)
        
        # Проверяем результаты
        assert sheet_id == MOCK_SHEET_ID
        assert url == MOCK_SHEET_URL
        mock_client.create.assert_called_once()
        mock_worksheet.update_title.assert_called_once()
        mock_spreadsheet.share.assert_called_once()
    
    @patch('gspread.authorize')
    @patch('google.oauth2.service_account.Credentials.from_service_account_file')
    def test_add_tasks(self, mock_creds, mock_authorize):
        """Тест добавления задач в таблицу."""
        # Настраиваем моки
        mock_client = MagicMock()
        mock_authorize.return_value = mock_client
        
        mock_spreadsheet = MagicMock()
        mock_client.open_by_key.return_value = mock_spreadsheet
        
        mock_worksheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        
        # Мокаем получение текущей цели
        mock_cell = MagicMock()
        mock_cell.value = MOCK_GOAL
        mock_worksheet.acell.return_value = mock_cell
        
        # Создаем объект и вызываем тестируемый метод
        gs = gsheet.GoogleSheetsManager()
        gs.add_tasks(MOCK_SHEET_ID, MOCK_TASKS)
        
        # Проверяем результаты
        mock_client.open_by_key.assert_called_once_with(MOCK_SHEET_ID)
        mock_spreadsheet.worksheet.assert_called_once_with(config.DEFAULT_SHEET_NAME)
        mock_worksheet.acell.assert_called_once_with('B2')
        
        # Проверяем, что append_row вызван для каждой задачи
        assert mock_worksheet.append_row.call_count == len(MOCK_TASKS)
    
    @patch('gspread.authorize')
    @patch('google.oauth2.service_account.Credentials.from_service_account_file')
    def test_update_task_status(self, mock_creds, mock_authorize):
        """Тест обновления статуса задачи."""
        # Настраиваем моки
        mock_client = MagicMock()
        mock_authorize.return_value = mock_client
        
        mock_spreadsheet = MagicMock()
        mock_client.open_by_key.return_value = mock_spreadsheet
        
        mock_worksheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        
        # Мокаем получение данных
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        mock_data = [
            {config.SHEET_COLUMNS[0]: today, config.SHEET_COLUMNS[1]: MOCK_GOAL, 
             config.SHEET_COLUMNS[2]: MOCK_TASKS[0], config.SHEET_COLUMNS[3]: "Не выполнено"}
        ]
        mock_worksheet.get_all_records.return_value = mock_data
        
        # Создаем объект и вызываем тестируемый метод
        gs = gsheet.GoogleSheetsManager()
        result = gs.update_task_status(MOCK_SHEET_ID, 0, "Выполнено")
        
        # Проверяем результаты
        assert result is True
        mock_worksheet.update.assert_called_once()

class TestCore:
    """Тесты для модуля core."""
    
    @patch('core.llm.generate_improved_goal')
    @patch('core.llm.generate_daily_tasks')
    def test_set_goal(self, mock_gen_tasks, mock_gen_goal):
        """Тест установки цели."""
        # Настраиваем моки
        mock_gen_goal.return_value = MOCK_IMPROVED_GOAL
        mock_gen_tasks.return_value = MOCK_TASKS
        
        # Мокаем GoogleSheetsManager
        mock_sheets = MagicMock()
        mock_sheets.create_user_spreadsheet.return_value = (MOCK_SHEET_ID, MOCK_SHEET_URL)
        
        # Создаем объект и вызываем тестируемый метод
        assistant = core.GoalAssistant()
        assistant.sheets_manager = mock_sheets
        improved_goal, url = assistant.set_goal(MOCK_USER_ID, MOCK_GOAL)
        
        # Проверяем результаты
        assert improved_goal == MOCK_IMPROVED_GOAL
        assert url == MOCK_SHEET_URL
        mock_gen_goal.assert_called_once_with(MOCK_GOAL)
        mock_sheets.add_goal.assert_called_once_with(MOCK_SHEET_ID, MOCK_IMPROVED_GOAL)
    
    @patch('core.llm.generate_daily_tasks')
    def test_generate_daily_tasks(self, mock_gen_tasks):
        """Тест генерации ежедневных задач."""
        # Настраиваем моки
        mock_gen_tasks.return_value = MOCK_TASKS
        
        # Мокаем GoogleSheetsManager
        mock_sheets = MagicMock()
        mock_sheets.get_user_spreadsheet = MagicMock(return_value=(MOCK_SHEET_ID, MOCK_SHEET_URL))
        mock_sheets.get_goal.return_value = MOCK_GOAL
        
        # Создаем объект и вызываем тестируемый метод
        assistant = core.GoalAssistant()
        assistant.sheets_manager = mock_sheets
        assistant.user_spreadsheets[MOCK_USER_ID] = (MOCK_SHEET_ID, MOCK_SHEET_URL)
        
        tasks, url = assistant.generate_daily_tasks(MOCK_USER_ID)
        
        # Проверяем результаты
        assert tasks == MOCK_TASKS
        assert url == MOCK_SHEET_URL
        mock_gen_tasks.assert_called_once_with(MOCK_GOAL)
        mock_sheets.add_tasks.assert_called_once_with(MOCK_SHEET_ID, MOCK_TASKS)
    
    def test_get_random_motivation(self):
        """Тест получения случайного мотивационного сообщения."""
        # Мокаем случайный выбор
        with patch('random.choice', return_value=config.MOTIVATIONAL_MESSAGES[0]):
            assistant = core.GoalAssistant()
            message = assistant.get_random_motivation()
            
            assert message == config.MOTIVATIONAL_MESSAGES[0]

if __name__ == "__main__":
    pytest.main(["-v", "tests.py"]) 