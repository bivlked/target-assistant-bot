from __future__ import annotations

import json
import logging
from typing import Any, List

from openai import AsyncOpenAI, APIError
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
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
    def __init__(self):
        self.client = AsyncOpenAI(api_key=openai_cfg.api_key)
        self.model = openai_cfg.model

    # -------------------------- Вспомогательные -------------------------
    @staticmethod
    def _extract_plan(content: str) -> List[dict[str, Any]]:  # noqa: D401
        start = content.find("[")
        end = content.rfind("]")
        if start == -1 or end == -1:
            raise ValueError("JSON-список не найден в ответе LLM")
        return json.loads(content[start : end + 1])

    # --------------------------- Публичные -----------------------------
    @RETRY
    async def generate_plan(
        self, goal_text: str, deadline_str: str, available_time_str: str
    ):
        prompt = (
            "Составь план достижения цели '{goal}' с дедлайном '{deadline}' "
            "и ежедневным временем '{time}' в формате JSON".format(
                goal=goal_text, deadline=deadline_str, time=available_time_str
            )
        )
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        content = resp.choices[0].message.content
        return self._extract_plan(content)
