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
from utils.retry_decorators import retry_openai_llm

logger = logging.getLogger(__name__)

RETRY = retry(
    retry=retry_if_exception_type(APIError),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(openai_cfg.max_retries),
)


class AsyncLLMClient:
    """Asynchronous client for OpenAI Chat Completions.

    Wraps the `openai.AsyncOpenAI` client and provides high-level methods
    for generating plans and motivational messages. Includes Tenacity retry logic
    and Prometheus metrics integration.

    Implements the `AsyncLLMInterface` protocol.
    """

    def __init__(self):
        """Initializes the AsyncOpenAI client using configuration from `config.openai_cfg`."""
        self.client = AsyncOpenAI(api_key=openai_cfg.api_key)
        self.model = openai_cfg.model

    # -------------------------- Вспомогательные -------------------------
    @staticmethod
    def _extract_plan(content: str) -> List[dict[str, Any]]:
        """Attempts to extract a JSON array of tasks from LLM text output.

        This is a simplified parser assuming the main content is the JSON array.
        It may need to be made more robust if the LLM often includes surrounding text.

        Raises:
            ValueError: If a JSON list is not found.
            json.JSONDecodeError: If the extracted string is not valid JSON.
        """
        start = content.find("[")
        end = content.rfind("]")
        if start == -1 or end == -1:
            raise ValueError("JSON-список не найден в ответе LLM")
        return json.loads(content[start : end + 1])

    # --------------------------- Публичные -----------------------------
    @retry_openai_llm
    async def generate_plan(
        self, goal_text: str, deadline_str: str, available_time_str: str
    ):
        """Asynchronously generates a daily task plan using the LLM.

        Attempts to use OpenAI's JSON mode for a structured response.

        Args:
            goal_text: Description of the user's goal.
            deadline_str: Deadline for achieving the goal.
            available_time_str: Approximate daily time commitment.

        Returns:
            A list of dictionaries representing daily tasks.

        Raises:
            OpenAI_APIError: If LLM call fails after retries.
            ValueError/json.JSONDecodeError: If response parsing fails.
        """
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

    @retry_openai_llm
    async def generate_motivation(self, goal_text: str, progress_summary: str) -> str:
        """Asynchronously generates a short motivational message in Russian.

        Args:
            goal_text: The user's goal text.
            progress_summary: A summary of the user's current progress.

        Returns:
            A motivational string.

        Raises:
            OpenAI_APIError: If LLM call fails after retries.
        """
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
