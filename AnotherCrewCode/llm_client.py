"""
Модуль клиента для работы с языковыми моделями OpenAI.
"""
import time
import logging
import re
import random
import json
from typing import Dict, List, Optional

import openai
from openai import OpenAI
import config

# Настройка логирования
logger = logging.getLogger(__name__)

class LLMClient:
    """Клиент для работы с языковой моделью."""
    
    def __init__(self, api_key=None):
        """
        Инициализирует клиент LLM.
        
        Args:
            api_key: API-ключ для доступа к LLM-сервису
        """
        self.api_key = api_key or config.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key)

    def generate_full_plan(self, goal, deadline, available_time=None):
        """
        Генерирует полный план достижения цели на весь период.
        
        Args:
            goal: Текст цели
            deadline: Срок достижения цели (строка, например "30 дней", "2 месяца")
            available_time: Доступное ежедневное время (строка, опционально)
            
        Returns:
            Словарь с планом, где ключи - даты, значения - списки задач на день
        """
        import datetime
        
        # Используем значения по умолчанию, если параметры не переданы
        available_time = available_time or "1-2 часа"
        
        # Определяем количество дней на основе deadline
        days_match = re.search(r'(\d+)\s*дн', deadline, re.IGNORECASE)
        weeks_match = re.search(r'(\d+)\s*недел', deadline, re.IGNORECASE)
        months_match = re.search(r'(\d+)\s*месяц|месяц|месяца|месяцев', deadline, re.IGNORECASE)
        
        total_days = 30  # значение по умолчанию
        
        if days_match:
            total_days = int(days_match.group(1))
        elif weeks_match:
            total_days = int(weeks_match.group(1)) * 7
        elif months_match:
            # Если есть число перед "месяц"
            if months_match.group(1):
                total_days = int(months_match.group(1)) * 30
            else:
                total_days = 30
                
        # Ограничиваем максимальное количество дней до 90
        total_days = min(total_days, 90)
        
        # Генерируем даты для плана
        today = datetime.datetime.now()
        dates = [(today + datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(total_days)]
        
        prompt = f"""
Создай детальный план достижения следующей цели: "{goal}".

Срок достижения цели: {deadline}.
Доступное время ежедневно: {available_time}.

План должен включать ТОЛЬКО ОДНУ конкретную важную задачу на каждый день в течение всего срока ({total_days} дней).
Каждая задача должна быть чёткой, конкретной и выполнимой за один день.

ВАЖНО: Каждый день содержит ТОЛЬКО ОДНУ задачу, не более!

Учитывай логическую последовательность: сначала подготовительные задачи, затем основные, потом завершающие.
Обязательно учитывай постепенное нарастание сложности и наличие дней отдыха.

Верни результат в формате JSON:
```json
{{
  "YYYY-MM-DD": ["Одна задача на день"],
  "YYYY-MM-DD": ["Одна задача на следующий день"],
  ...
}}
```

Даты должны быть реальными, начиная с сегодняшнего дня: {dates[0]}.

ОЧЕНЬ ВАЖНО: убедись, что JSON правильно форматирован, без ошибок синтаксиса. Используй двойные кавычки для ключей и значений!
"""
        
        # Отправляем запрос к модели
        response = self.client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Ты - эксперт по планированию и достижению целей, создающий детальные и реалистичные планы."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.7
        )
        
        # Извлекаем JSON из ответа
        content = response.choices[0].message.content
        try:
            # Попытка найти JSON в формате ```json ... ```
            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                # Дополнительная очистка строки от возможных проблемных символов
                json_str = json_str.strip().replace('\n', '')
                # Проверяем и исправляем кавычки
                json_str = re.sub(r"(?<!\\)'([^']*)'", r'"\1"', json_str)
                plan = json.loads(json_str)
            else:
                # Если не нашли в markdown формате, пробуем напрямую парсить весь ответ
                # Сначала проверяем, начинается ли ответ с {
                if content.strip().startswith('{') and content.strip().endswith('}'):
                    # Очищаем от возможных проблемных символов
                    content = content.strip().replace('\n', '')
                    # Проверяем и исправляем кавычки
                    content = re.sub(r"(?<!\\)'([^']*)'", r'"\1"', content)
                    plan = json.loads(content)
                else:
                    # Если не похоже на JSON, используем план по умолчанию
                    logger.warning(f"Не удалось найти JSON в ответе LLM: {content[:100]}...")
                    raise ValueError("Неверный формат JSON в ответе")
                
            # Проверяем, что план не пустой и содержит задачи для каждого дня
            if not plan:
                logger.warning("LLM вернул пустой план")
                plan = {dates[0]: ["Начать работу над целью"]}
            
            # Проверяем формат дат и преобразуем их, если нужно
            corrected_plan = {}
            for date_str, tasks in plan.items():
                # Если дата в неправильном формате, пытаемся распознать её
                try:
                    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                        corrected_date = date_str  # Дата уже в правильном формате
                    else:
                        # Попытка распознать другие форматы даты
                        date_match = re.search(r'(\d{1,4})[-/.](\d{1,2})[-/.](\d{1,4})', date_str)
                        if date_match:
                            year, month, day = date_match.groups()
                            if len(year) == 2:
                                year = '20' + year
                            if len(day) == 4:
                                # Возможно, год и день перепутаны местами
                                year, day = day, year
                            corrected_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        else:
                            # Если не удалось распознать дату, пропускаем
                            continue
                    
                    # Проверяем, что задачи - это список строк
                    if isinstance(tasks, list):
                        # Берем только первую задачу
                        task_list = []
                        for task in tasks:
                            if isinstance(task, str) and task.strip():
                                task_list.append(task.strip())
                                break  # Берем только первую задачу
                        if task_list:
                            corrected_plan[corrected_date] = task_list
                except Exception as e:
                    logger.warning(f"Ошибка при обработке даты {date_str}: {e}")
            
            # Если после коррекции план пустой, используем план по умолчанию
            if not corrected_plan:
                logger.warning("После коррекции план пустой, использую план по умолчанию")
                corrected_plan = {dates[0]: ["Начать работу над целью"]}
            
            # Добавляем отсутствующие даты, если есть
            for date in dates:
                if date not in corrected_plan:
                    corrected_plan[date] = ["Работа над целью на этот день"]
            
            # Убеждаемся, что в каждом дне только одна задача
            for date in corrected_plan:
                if len(corrected_plan[date]) > 1:
                    corrected_plan[date] = [corrected_plan[date][0]]
                    
            return corrected_plan
            
        except Exception as e:
            logger.error(f"Ошибка при обработке плана из LLM: {e}")
            # Возвращаем простой план по умолчанию
            default_plan = {}
            for date in dates:
                default_plan[date] = ["Работа над целью"]
            return default_plan

    def generate_clarifying_questions(self, initial_goal):
        """
        Генерирует уточняющие вопросы по начальной цели пользователя.
        
        Args:
            initial_goal: Исходная формулировка цели
            
        Returns:
            Список строк с уточняющими вопросами
        """
        # Создаем запрос для получения уточняющих вопросов
        questions_prompt = f"""
Помоги пользователю уточнить цель: "{initial_goal}"

Задай 2-3 вопроса, которые помогут сделать цель более конкретной и измеримой.
ОБЯЗАТЕЛЬНО спроси о:
1. Сроке, за который пользователь хочет достичь цели (если он не указан в исходной цели)
2. Сколько времени ежедневно пользователь готов уделять для достижения цели (если не указано)

Сформулируй вопросы вежливо, в формате нумерованного списка.
Верни вопросы в виде списка, чтобы каждый вопрос был отдельным элементом списка.
"""
        
        try:
            # Отправляем запрос к модели
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Ты - эксперт по планированию и достижению целей."},
                    {"role": "user", "content": questions_prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            # Извлекаем текст с вопросами
            questions_text = response.choices[0].message.content
            
            # Разбираем текст на отдельные вопросы
            questions = []
            # Ищем вопросы в формате нумерованного списка (1. Вопрос)
            for line in questions_text.split('\n'):
                line = line.strip()
                if re.match(r'^\d+\.', line):
                    # Убираем номер и начальные пробелы
                    clean_question = re.sub(r'^\d+\.\s*', '', line).strip()
                    if clean_question:
                        questions.append(clean_question)
            
            # Если не нашли вопросы в нумерованном списке, разбиваем по строкам
            if not questions:
                questions = [line.strip() for line in questions_text.strip().split('\n') if line.strip() and '?' in line]
            
            # Если все еще нет вопросов, создаем стандартные
            if not questions:
                questions = [
                    "За какой срок вы планируете достичь цели?",
                    "Сколько времени ежедневно вы готовы уделять для достижения цели?"
                ]
            
            return questions
            
        except Exception as e:
            logger.error(f"Ошибка при генерации уточняющих вопросов: {e}")
            # Возвращаем стандартные вопросы в случае ошибки
            return [
                "За какой срок вы планируете достичь цели?",
                "Сколько времени ежедневно вы готовы уделять для достижения цели?"
            ]

    def extract_goal_parameters(self, text):
        """
        Извлекает информацию о сроках и доступном времени из текста пользователя.
        
        Args:
            text: Текст цели и уточнений пользователя
            
        Returns:
            Словарь с параметрами "goal", "available_time" и "deadline"
        """
        prompt = f"""
Извлеки из текста пользователя информацию о его цели, сроках выполнения и доступном ежедневном времени.
Если какой-то информации нет, используй разумные значения по умолчанию:
- Срок выполнения по умолчанию: "30 дней"
- Доступное время по умолчанию: "1 час в день"

Текст пользователя:
{text}

Верни результат ТОЛЬКО в формате JSON:
{{
  "goal": "Формулировка цели",
  "deadline": "Срок выполнения (например, '2 недели', '1 месяц')",
  "available_time": "Доступное ежедневное время (например, '30 минут', '2 часа')"
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Ты - ассистент по анализу целей и извлечению параметров."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            # Извлекаем JSON из ответа
            content = response.choices[0].message.content
            
            # Попытка найти JSON в формате ```json ... ```
            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                # Дополнительная очистка от возможных проблемных символов
                json_str = json_str.strip().replace('\n', '')
                result = json.loads(json_str)
            else:
                # Если не нашли в markdown формате, пробуем напрямую парсить весь ответ
                content = content.strip()
                if content.startswith('{') and content.endswith('}'):
                    result = json.loads(content)
                else:
                    # Если не похоже на JSON, используем значения по умолчанию
                    raise ValueError("Неверный формат ответа")
                    
            # Проверяем наличие всех необходимых полей
            if not all(key in result for key in ["goal", "deadline", "available_time"]):
                missing_keys = [key for key in ["goal", "deadline", "available_time"] if key not in result]
                logger.warning(f"В ответе отсутствуют ключи: {missing_keys}")
                
                # Добавляем отсутствующие поля со значениями по умолчанию
                if "goal" not in result:
                    result["goal"] = text
                if "deadline" not in result:
                    result["deadline"] = "30 дней"
                if "available_time" not in result:
                    result["available_time"] = "1 час"
                    
            return result
            
        except Exception as e:
            logger.warning(f"Ошибка при извлечении параметров цели: {e}")
            # Если произошла ошибка, возвращаем значения по умолчанию
            return {
                "goal": text,
                "deadline": "30 дней",
                "available_time": "1 час"
            }
