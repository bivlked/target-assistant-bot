from __future__ import annotations

import json
import logging
from typing import Any, List
import time

from openai import AsyncOpenAI, APIError
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)

from config import openai_cfg
from core.metrics import LLM_API_CALLS, LLM_API_LATENCY
from llm.prompts import SYSTEM_PROMPT

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
        """Requests a task plan from LLM, attempting to use JSON mode."""
        method_name = "generate_plan"
        start_time = time.monotonic()
        prompt = (
            "Составь план достижения цели '{goal}' с дедлайном '{deadline}' "
            "и ежедневным временем '{time}' в формате JSON".format(
                goal=goal_text, deadline=deadline_str, time=available_time_str
            )
        )
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        try:
            content = resp.choices[0].message.content
            LLM_API_CALLS.labels(method_name=method_name, status="success").inc()
            return self._extract_plan(content)
        except Exception as e:
            LLM_API_CALLS.labels(method_name=method_name, status="error").inc()
            logger.error(f"Error processing LLM response for {method_name}: {e}")
            raise
        finally:
            LLM_API_LATENCY.labels(method_name=method_name).observe(
                time.monotonic() - start_time
            )

    @RETRY
    async def generate_motivation(self, goal_text: str, progress_summary: str) -> str:
        method_name = "generate_motivation"
        start_time = time.monotonic()
        prompt = (
            "Ты - мотивационный коуч. Пользователь работает над целью: {goal}. "
            "Текущий прогресс: {progress}. "
            "Напиши вдохновляющее сообщение на русском из 2–3 коротких предложений (до 150 символов)."
        ).format(goal=goal_text, progress=progress_summary)
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        try:
            content = resp.choices[0].message.content.strip()
            LLM_API_CALLS.labels(method_name=method_name, status="success").inc()
            return content
        except Exception as e:
            LLM_API_CALLS.labels(method_name=method_name, status="error").inc()
            logger.error(f"Error processing LLM response for {method_name}: {e}")
            raise
        finally:
            LLM_API_LATENCY.labels(method_name=method_name).observe(
                time.monotonic() - start_time
            )
