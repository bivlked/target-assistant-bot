from __future__ import annotations

import json
import logging
from typing import Any, List
import re
import ast

from openai import OpenAI, APIError

from config import openai_cfg
from llm.prompts import PLAN_PROMPT, MOTIVATION_PROMPT

logger = logging.getLogger(__name__)


class LLMClient:
    """Упрощённый клиент OpenAI Chat Completion.

    Инкапсулирует логику повторных попыток, парсинга «шума» из ответов
    языковой модели и предоставляет два высокоуровневых метода:

    * :py:meth:`generate_plan` – вернуть JSON-план ежедневных задач;
    * :py:meth:`generate_motivation` – сгенерировать мотивационное сообщение.
    """

    def __init__(self):
        """Читает конфигурацию из ``config.openai_cfg`` и инициализирует SDK."""
        self.client = OpenAI(api_key=openai_cfg.api_key)
        self.model = openai_cfg.model
        self.max_retries = openai_cfg.max_retries

    def _chat_completion(self, prompt: str) -> str:
        """Базовый вызов ChatCompletion с автоматическим **retry**.

        Private-метод: используется публичными врапперами для обеспечения
        повторных попыток при `openai.APIError`. Количество попыток задаётся
        в конфиге.
        """
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                )
                return response.choices[0].message.content.strip()
            except APIError as e:
                logger.warning("Ошибка OpenAI: %s, попытка %d", e, attempt + 1)
                if attempt == self.max_retries:
                    raise

    def _extract_plan(self, content: str):
        """Пытается извлечь JSON-массив задач из произвольного текста LLM."""
        # Если ответ заключён в markdown блок ```json ... ``` или ``` ... ```
        md = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.S)
        if md:
            content = md.group(1)
        # Если в тексте есть первый '[' и последний ']', берём подстроку
        else:
            arr = re.search(r"\[.*\]", content, re.S)
            if arr:
                content = arr.group(0)
        # Замена одиночных кавычек на двойные для JSON
        content_clean = content.strip()
        # Простейшая попытка исправить trailing comma
        content_clean = re.sub(r",\s*]", "]", content_clean)
        try:
            return json.loads(content_clean)
        except json.JSONDecodeError:
            try:
                obj = ast.literal_eval(content_clean)
                # гарантируем список словарей с day/task
                if isinstance(obj, list):
                    return obj
            except Exception as e:
                logger.debug("literal_eval failed: %s", e)
        # если всё плохо - пробросим исключение вверх
        raise json.JSONDecodeError("Invalid JSON", content_clean, 0)

    # -------------------------------------------------
    # Публичные методы
    # -------------------------------------------------
    def generate_plan(
        self, goal_text: str, deadline: str, time: str
    ) -> List[dict[str, Any]]:
        """Запрашивает у LLM план задач и возвращает список словарей.

        Возвращаемый формат: ``[{"day": 1, "task": "..."}, ...]``.
        При необходимости выполняется «обратная совместимость» – метод
        пытается вытащить JSON из markdown-блоков или свободного текста.
        """
        prompt = PLAN_PROMPT.format(goal_text=goal_text, deadline=deadline, time=time)
        content = self._chat_completion(prompt)
        logger.debug("LLM raw plan response: %s", content[:2000])
        try:
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = self._extract_plan(content)
            # простая валидация
            if not isinstance(data, list) or not all(
                "day" in item and "task" in item for item in data
            ):
                raise ValueError("Неверный формат JSON от LLM")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Не удалось распарсить JSON от LLM: %s", e)
            raise

    def generate_motivation(self, goal_text: str, progress_summary: str) -> str:
        """Генерирует короткое мотивирующее сообщение на русском языке."""
        prompt = MOTIVATION_PROMPT.format(
            goal_text=goal_text, progress_summary=progress_summary
        )
        return self._chat_completion(prompt)
