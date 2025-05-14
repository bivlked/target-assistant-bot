from __future__ import annotations

import json
import logging
from typing import Any, List
import re
import ast
import time

from openai import OpenAI, APIError

from config import openai_cfg
from llm.prompts import PLAN_PROMPT, MOTIVATION_PROMPT, SYSTEM_PROMPT
from core.metrics import LLM_API_CALLS, LLM_API_LATENCY
from utils.retry_decorators import retry_openai_llm

logger = logging.getLogger(__name__)


class LLMClient:
    """Simplified synchronous client for OpenAI Chat Completions.

    Encapsulates retry logic, parsing of noisy responses from the language model,
    and provides two high-level methods:
    - `generate_plan()`: Returns a JSON plan of daily tasks.
    - `generate_motivation()`: Generates a motivational message.

    Uses Tenacity for retries and Prometheus for metrics.
    Implements the `LLMInterface` protocol.
    """

    def __init__(self):
        """Initializes the OpenAI client using configuration from `config.openai_cfg`."""
        self.client = OpenAI(api_key=openai_cfg.api_key)
        self.model = openai_cfg.model
        self.max_retries = (
            openai_cfg.max_retries
        )  # Used by retry_openai_llm decorator via config

    @retry_openai_llm
    def _chat_completion(self, prompt: str) -> str:
        """Base call to ChatCompletion with automatic retries via decorator.

        Args:
            prompt: The user prompt for the LLM.

        Returns:
            The content string from the LLM response.

        Raises:
            OpenAI_APIError: If all retry attempts fail.
        """
        # Manual retry loop and direct metric calls are now handled by the decorator.
        start_time = time.monotonic()
        method_name = (
            "chat_completion_generic"  # Or derive more specifically if possible
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            LLM_API_CALLS.labels(method_name=method_name, status="success").inc()
            return response.choices[0].message.content.strip()
        except APIError as e:  # This will be caught by Tenacity first if it matches
            LLM_API_CALLS.labels(method_name=method_name, status="error").inc()
            # Logger warning for final failure (if reraised) is handled by Tenacity's _log_retry
            raise e  # Re-raise for Tenacity to handle or for caller if Tenacity gives up
        finally:
            LLM_API_LATENCY.labels(method_name=method_name).observe(
                time.monotonic() - start_time
            )

    def _extract_plan(self, content: str):
        """Attempts to extract a JSON array of tasks from potentially noisy LLM text output.

        Handles markdown code blocks and attempts to clean common JSON issues.

        Raises:
            json.JSONDecodeError: If a valid JSON list cannot be extracted.
        """
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

    def _chat_completion_with_json_mode(self, prompt: str) -> str:
        """Specific chat completion call attempting to use JSON mode."""
        # This method will also be decorated by @retry_openai_llm implicitly if called by a decorated public method,
        # or can be decorated itself. For now, rely on public methods being decorated.
        start_time = time.monotonic()
        method_name = "generate_plan_json_mode"
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,  # Consider 0.2 for JSON
                response_format={"type": "json_object"},
            )
            LLM_API_CALLS.labels(method_name=method_name, status="success").inc()
            return response.choices[0].message.content.strip()
        except APIError as e:
            LLM_API_CALLS.labels(method_name=method_name, status="error").inc()
            raise e  # Re-raise for Tenacity or caller
        finally:
            LLM_API_LATENCY.labels(method_name=method_name).observe(
                time.monotonic() - start_time
            )

    # -------------------------------------------------
    # Публичные методы
    # -------------------------------------------------
    @retry_openai_llm  # Apply retry to public method as well, in case _chat_completion_with_json_mode is not decorated
    def generate_plan(
        self, goal_text: str, deadline: str, time: str
    ) -> List[dict[str, Any]]:
        """Generates a daily task plan to achieve a goal, using the LLM.

        Attempts to use OpenAI's JSON mode for a structured response.
        Includes retry logic and metrics.

        Args:
            goal_text: Description of the user's goal.
            deadline: Deadline for achieving the goal.
            time: Approximate daily time commitment.

        Returns:
            A list of dictionaries, where each dictionary represents a daily task
            (e.g., `[{"day": 1, "task": "Complete module X"}, ...]`).

        Raises:
            OpenAI_APIError: If LLM call fails after retries.
            json.JSONDecodeError: If the LLM response cannot be parsed into a valid plan.
            ValueError: If the parsed JSON does not match the expected plan format.
        """
        prompt = PLAN_PROMPT.format(goal_text=goal_text, deadline=deadline, time=time)
        # Attempt to use JSON mode with a fallback if not supported or if there's an issue.
        # The _chat_completion method itself might need adjustment if it doesn't pass through response_format.
        # For now, we assume _chat_completion is generic and we handle json_format here if possible,
        # or rely on _extract_plan for robustness.

        # This direct call bypasses _chat_completion's retry/metric logic for the JSON mode attempt.
        # A more robust solution would integrate response_format into _chat_completion.
        # For simplicity now, let's assume we modify _chat_completion to accept response_format.

        content = self._chat_completion_with_json_mode(prompt)
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
        """Generates a short motivational message in Russian using the LLM.

        Includes retry logic and metrics.

        Args:
            goal_text: The user's goal text.
            progress_summary: A summary of the user's current progress.

        Returns:
            A motivational string.

        Raises:
            OpenAI_APIError: If LLM call fails after retries.
        """
        prompt = MOTIVATION_PROMPT.format(
            goal_text=goal_text, progress_summary=progress_summary
        )
        return self._chat_completion(prompt)
