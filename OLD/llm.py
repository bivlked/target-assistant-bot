"""
Модуль для работы с OpenAI API.

Предоставляет функции для взаимодействия с языковыми моделями OpenAI.
"""
import time
import logging
from functools import wraps
from typing import Any, Dict, List, Optional, Callable
import re
import datetime
import random

import openai
from openai import OpenAI
import config

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI
client = OpenAI(api_key=config.OPENAI_API_KEY)

def catch_errors(func: Callable) -> Callable:
    """
    Декоратор для обработки ошибок при работе с OpenAI API.
    
    Args:
        func: Функция для декорирования
        
    Returns:
        Декорированная функция с обработкой ошибок
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = config.OPENAI_MAX_RETRIES
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                return func(*args, **kwargs)
            except openai.RateLimitError:
                wait_time = 2 ** retry_count
                logger.warning(f"Превышен лимит запросов к API. Ожидание {wait_time} секунд...")
                time.sleep(wait_time)
                retry_count += 1
            except openai.APITimeoutError:
                wait_time = 2 ** retry_count
                logger.warning(f"Таймаут запроса к API. Ожидание {wait_time} секунд...")
                time.sleep(wait_time)
                retry_count += 1
            except openai.APIError as e:
                logger.error(f"Ошибка API OpenAI: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Неожиданная ошибка при запросе к OpenAI: {str(e)}")
                raise
                
        logger.error(f"Превышено максимальное число попыток: {max_retries}")
        raise Exception("Не удалось получить ответ от OpenAI API после нескольких попыток")
    
    return wrapper

@catch_errors
def generate_improved_goal(goal: str) -> str:
    """
    Генерирует улучшенную версию цели с помощью OpenAI.
    
    Args:
        goal: Исходная формулировка цели от пользователя
        
    Returns:
        Улучшенная формулировка цели
    """
    prompt = config.GOAL_PROMPT_TEMPLATE.format(goal=goal)
    
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": config.GOAL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        timeout=config.OPENAI_TIMEOUT
    )
    
    return response.choices[0].message.content

@catch_errors
def generate_daily_tasks(goal: str, today_date: str) -> List[str]:
    """
    Генерирует список ежедневных задач для достижения цели с помощью OpenAI.
    
    Args:
        goal: Формулировка цели
        today_date: Текущая дата в формате строки
        
    Returns:
        Список задач на день
    """
    # Используем шаблонный промпт из конфигурации
    # Для простой версии функции используем стандартные значения для available_time и deadline
    prompt = config.TASKS_PROMPT_TEMPLATE.format(
        goal=goal,
        available_time="2-3 часа",
        deadline="две недели"
    )
    
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": config.TASKS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        timeout=config.OPENAI_TIMEOUT
    )
    
    tasks_text = response.choices[0].message.content
    return extract_tasks_from_text(tasks_text)

def extract_tasks_from_text(text: str) -> List[str]:
    """
    Извлекает задачи из текстового ответа LLM.
    
    Args:
        text: Текст, содержащий список задач
        
    Returns:
        Список задач
    """
    tasks = []
    # Разделяем текст на строки и ищем задачи с номерами или маркерами
    for line in text.strip().split('\n'):
        line = line.strip()
        # Ищем нумерованные строки (1. Task) или строки с маркерами (- Task)
        if re.match(r'^\d+\.|\-|\*', line):
            # Удаляем цифры/маркеры и лишние пробелы
            task = re.sub(r'^\d+\.|\-|\*\s*', '', line).strip()
            if task:
                tasks.append(task)
    
    # Если не нашли задачи в ожидаемом формате, просто разделяем по строкам
    if not tasks and text.strip():
        tasks = [line.strip() for line in text.strip().split('\n') if line.strip()]
        
    return tasks

class LLMClient:
    """Клиент для работы с языковой моделью."""
    
    def __init__(self, api_key=None):
        """
        Инициализирует клиент LLM.
        
        Args:
            api_key: API-ключ для доступа к LLM-сервису
        """
        self.api_key = api_key or config.OPENAI_API_KEY
        self.client = openai.OpenAI(api_key=self.api_key)

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
        import re
        import json
        
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
            Строка с уточняющими вопросами
        """
        # Создаем запрос для получения уточняющих вопросов
        questions_prompt = f"""
Помоги пользователю уточнить цель: "{initial_goal}"

Задай 2-3 вопроса, которые помогут сделать цель более конкретной и измеримой.
ОБЯЗАТЕЛЬНО спроси о:
1. Сроке, за который пользователь хочет достичь цели (если он не указан в исходной цели)
2. Сколько времени ежедневно пользователь готов уделять для достижения цели (если не указано)

Сформулируй вопросы вежливо, в формате нумерованного списка.
"""
        
        # Отправляем запрос к модели
        response = self.client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": config.GOAL_SYSTEM_PROMPT},
                {"role": "user", "content": questions_prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        # Возвращаем текст с вопросами
        return response.choices[0].message.content

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
Если какой-то информации нет, используй разумные значения по умолчанию.

Текст пользователя:
{text}

Верни результат в формате JSON:
```json
{{
  "goal": "Формулировка цели",
  "deadline": "Срок выполнения (например, '2 недели', '1 месяц')",
  "available_time": "Доступное ежедневное время (например, '30 минут', '2 часа')"
}}
```
"""
        
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
        try:
            # Попытка найти JSON в формате ```json ... ```
            import json
            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # Если не нашли в markdown формате, пробуем напрямую парсить весь ответ
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Не удалось распарсить JSON из ответа LLM: {e}")
            # Если не удалось распарсить JSON, возвращаем значения по умолчанию
            return {
                "goal": text,
                "deadline": "30 дней",
                "available_time": "1 час"
            }

    def improve_goal(self, goal_text, questions=None, answers=None):
        """
        Улучшает формулировку цели пользователя на основе исходной цели и уточнений.
        
        Args:
            goal_text: Исходная формулировка цели
            questions: Уточняющие вопросы (опционально)
            answers: Ответы пользователя на уточняющие вопросы (опционально)
            
        Returns:
            Улучшенная формулировка цели
        """
        # Если есть вопросы и ответы, включаем их в промпт
        if questions and answers:
            prompt = f"""
Исходная цель пользователя: {goal_text}

Уточняющие вопросы:
{questions}

Ответы пользователя:
{answers}

На основе исходной цели и ответов пользователя, сформулируй более конкретную, 
измеримую и достижимую цель. Формулировка должна включать все важные детали, 
такие как сроки, количественные показатели и условия достижения.
"""
        else:
            # Используем базовый шаблон, если нет уточнений
            prompt = config.GOAL_PROMPT_TEMPLATE.format(goal=goal_text)
        
        response = self.client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": config.GOAL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        improved_goal = response.choices[0].message.content
        return improved_goal
        
    def generate_daily_tasks(self, goal, available_time=None, deadline=None):
        """
        Генерирует список ежедневных задач для достижения цели.
        
        Args:
            goal: Текст цели
            available_time: Доступное ежедневное время (строка, опционально)
            deadline: Срок достижения цели (строка, опционально)
            
        Returns:
            Список задач на день
        """
        # Используем значения по умолчанию, если параметры не переданы
        available_time = available_time or "2-3 часа"
        deadline = deadline or "две недели"
        
        # Используем шаблон промпта из конфигурации
        prompt = config.TASKS_PROMPT_TEMPLATE.format(
            goal=goal,
            available_time=available_time,
            deadline=deadline
        )
        
        response = self.client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": config.TASKS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        tasks_text = response.choices[0].message.content
        return extract_tasks_from_text(tasks_text)

    def generate_motivation(self, goal, progress_percent=None, completed_tasks=None, total_tasks=None):
        """
        Генерирует персонализированное мотивационное сообщение на основе цели и прогресса пользователя.
        
        Args:
            goal: Текст цели пользователя
            progress_percent: Процент выполнения плана (опционально)
            completed_tasks: Количество выполненных задач (опционально)
            total_tasks: Общее количество задач (опционально)
            
        Returns:
            Строка с персонализированным мотивационным сообщением
        """
        # Определяем тип сообщения на основе прогресса
        message_type = "общее"
        progress_info = ""
        
        if progress_percent is not None:
            progress_info = f"Прогресс: {progress_percent}%."
            if progress_percent < 20:
                message_type = "начальный этап"
            elif progress_percent < 50:
                message_type = "середина пути"
            elif progress_percent < 80:
                message_type = "ближе к цели"
            else:
                message_type = "финальный этап"
        
        if completed_tasks is not None and total_tasks is not None:
            if not progress_info:
                progress_info = f"Выполнено {completed_tasks} из {total_tasks} задач."
        
        prompt = f"""
Напиши короткое мотивационное сообщение (1-2 предложения) для человека, который стремится к следующей цели:
"{goal}"

{progress_info}

Тип мотивации: {message_type}

Сообщение должно быть:
- Персонализированным и связанным с указанной целью
- Позитивным и вдохновляющим
- Кратким (максимум 2 предложения)
- Без излишних клише и банальностей
- С использованием метафор/аналогий, связанных с целью
"""
        
        try:
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Ты - позитивный и вдохновляющий коуч, помогающий людям достигать целей."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            motivation = response.choices[0].message.content
            
            # Очищаем от кавычек, если они есть
            motivation = motivation.strip('"\'')
            
            return motivation
        except Exception as e:
            logger.error(f"Ошибка при генерации мотивационного сообщения: {e}")
            # Возвращаем стандартное сообщение в случае ошибки
            return random.choice(config.MOTIVATIONAL_MESSAGES)

    def generate_plan_progress_report(self, goal, completed_tasks, remaining_tasks, days_remaining, available_time=""):
        """
        Генерирует аналитический отчет о прогрессе выполнения плана.
        
        Args:
            goal (str): Цель пользователя
            completed_tasks (list): Список выполненных задач как словарей с ключами 'date', 'text', 'status'
            remaining_tasks (list): Список оставшихся задач как словарей с ключами 'date', 'text', 'status'
            days_remaining (int): Количество дней до дедлайна
            available_time (str): Доступное время пользователя в день
            
        Returns:
            str: Отчет о прогрессе с рекомендациями
        """
        logger.info("Генерация отчета о прогрессе плана")
        
        # Подготовка данных для запроса
        total_tasks = len(completed_tasks) + len(remaining_tasks)
        completion_percentage = 0
        if total_tasks > 0:
            completion_percentage = (len(completed_tasks) / total_tasks) * 100
        
        # Форматирование задач для передачи в запрос
        completed_task_texts = [f"{task['date']}: {task['text']}" for task in completed_tasks]
        remaining_task_texts = [f"{task['date']}: {task['text']}" for task in remaining_tasks]
        
        # Подготовка промпта
        prompt = f"""Ты - профессиональный аналитик и тренер по продуктивности. Составь краткий отчет о прогрессе 
        выполнения плана, основываясь на следующих данных:
        
        ЦЕЛЬ ПОЛЬЗОВАТЕЛЯ: {goal}
        
        ПРОГРЕСС: {len(completed_tasks)} из {total_tasks} задач выполнено ({completion_percentage:.1f}%)
        
        ДНЕЙ ДО ДЕДЛАЙНА: {days_remaining}
        
        ДОСТУПНОЕ ВРЕМЯ В ДЕНЬ: {available_time}
        
        ВЫПОЛНЕННЫЕ ЗАДАЧИ:
        {chr(10).join(completed_task_texts[:5]) if completed_task_texts else "Нет выполненных задач"}
        {f'... и еще {len(completed_task_texts) - 5} задач' if len(completed_task_texts) > 5 else ''}
        
        ОСТАВШИЕСЯ ЗАДАЧИ:
        {chr(10).join(remaining_task_texts[:5]) if remaining_task_texts else "Нет оставшихся задач"}
        {f'... и еще {len(remaining_task_texts) - 5} задач' if len(remaining_task_texts) > 5 else ''}
        
        Дай четкую оценку текущего прогресса, упомяни успехи и сложности. Предложи 2-3 конкретные рекомендации 
        для улучшения результатов. Если прогресс отличный - похвали. Если есть отставание - дай мотивирующие 
        советы. Учти оставшееся время и объем задач. Ответ должен быть структурированным, но лаконичным - не более 
        10 предложений общей длиной до 250 слов. Используй эмодзи для наглядности.
        """
        
        try:
            # Отправляем запрос с использованием метода chat.completions
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Ты - аналитик прогресса и эксперт по достижению целей, который дает точные и полезные оценки и рекомендации."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            # Получаем результат
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Ошибка при создании отчета о прогрессе: {e}", exc_info=True)
            return "Не удалось создать отчет о прогрессе. Пожалуйста, попробуйте позже."

if __name__ == "__main__":
    # Тестирование модуля
    test_goal = "Хочу похудеть"
    improved = generate_improved_goal(test_goal)
    print(f"Улучшенная цель: {improved}")
    
    tasks = generate_daily_tasks("Похудеть на 5 кг за 2 месяца", "2024-04-15")
    print("\nЗадачи на сегодня:")
    for i, task in enumerate(tasks, 1):
        print(f"{i}. {task}")
    
    # Тестирование новой функции extract_goal_parameters
    print("\n--- Тестирование extract_goal_parameters ---")
    
    test_inputs = [
        "Хочу научиться плавать за неделю и готов тратить на это два часа в день",
        "Исходная цель: Выучить испанский\n\nУточняющие вопросы: 1. За какой срок вы хотите достичь базового уровня? 2. Сколько времени в день вы готовы уделять?\n\nОтветы пользователя: Хочу за 3 месяца. Могу заниматься по 30 минут каждый день",
        "Хочу подготовиться к марафону"
    ]
    
    llm_client = LLMClient()
    for test_input in test_inputs:
        result = llm_client.extract_goal_parameters(test_input)
        print(f"\nВвод: {test_input[:50]}...")
        print(f"Результат: {result}") 