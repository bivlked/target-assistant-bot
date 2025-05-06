from __future__ import annotations

import json
import logging
from typing import Any, List

from openai import AsyncOpenAI, APIError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config import openai_cfg

logger = logging.getLogger(__name__)

RETRY = retry(
    retry=retry_if_exception_type(APIError),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(openai_cfg.max_retries),
)


class AsyncLLMClient:
    """Асинхронный клиент OpenAI: generate_plan и generate_motivation."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=openai_cfg.api_key)
        self.model = openai_cfg.model

    # -------------------------- helpers ---------------------------
    @staticmethod
    def _extract_plan(content: str) -> List[dict[str, Any]]:  # noqa: D401
        start = content.find("[")
        end = content.rfind("]")
        if start == -1 or end == -1:
            raise ValueError("JSON-список не найден в ответе LLM")
        return json.loads(content[start : end + 1])

    # --------------------------- public ---------------------------
    @RETRY
    async def generate_plan(
        self, goal_text: str, deadline_str: str, available_time_str: str
    ) -> List[dict[str, Any]]:
        prompt = (
            "Составь план достижения цели '{goal}' с дедлайном '{deadline}' "
            "и ежедневным временем '{time}' в формате JSON"
        ).format(goal=goal_text, deadline=deadline_str, time=available_time_str)
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        content = resp.choices[0].message.content
        return self._extract_plan(content)

    @RETRY
    async def generate_motivation(self, goal_text: str, progress_summary: str) -> str:
        prompt = (
            "Ты - мотивационный коуч. Пользователь работает над целью: {goal}. "
            "Текущий прогресс: {progress}. "
            "Напиши вдохновляющее сообщение на русском из 2–3 коротких предложений (до 150 символов)."
        ).format(goal=goal_text, progress=progress_summary)
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()