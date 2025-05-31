"""Asynchronous client for interacting with OpenAI LLM services."""

from __future__ import annotations

import json
import structlog
from typing import Any, List
import time
import re
import ast

from openai import AsyncOpenAI

from config import openai_cfg
from core.metrics import LLM_API_CALLS, LLM_API_LATENCY

from llm.prompts import SYSTEM_PROMPT

from utils.retry_decorators import retry_openai_llm

logger = structlog.get_logger(__name__)


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

    # -------------------------- Helper methods -------------------------
    @staticmethod
    def _extract_plan(content: str) -> List[dict[str, Any]]:
        """Attempts to extract a JSON array of tasks from potentially noisy LLM text output.

        Handles markdown code blocks and attempts to clean common JSON issues.
        This logic is similar to the one previously in the synchronous LLMClient.

        Raises:
            json.JSONDecodeError: If a valid JSON list cannot be extracted after attempts.
            ValueError: If a list structure is not ultimately found or parsed.
        """
        # If response is wrapped in markdown code block ```json ... ``` or ``` ... ```
        md_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.DOTALL)
        if md_match:
            json_str = md_match.group(1)
        else:
            # If not in markdown, try to find the outermost list brackets
            list_match = re.search(r"\[.*\]", content, re.DOTALL)
            if list_match:
                json_str = list_match.group(0)
            else:
                # If no brackets found, or if it's not a list, this will likely fail later
                # or might be an object, which we don't want for a plan.
                json_str = (
                    content.strip()
                )  # As a last resort, try to parse the whole cleaned content

        json_str_cleaned = json_str.strip()
        # Simplistic attempt to fix trailing commas that break json.loads
        json_str_cleaned = re.sub(r",\s*([}\]])", r"\1", json_str_cleaned)

        try:
            data = json.loads(json_str_cleaned)
            if not isinstance(data, list):
                raise ValueError("Extracted JSON is not a list.")
            # Optional: further validation that items are dicts with 'day' and 'task'
            # for item in data:
            #     if not (isinstance(item, dict) and "day" in item and "task" in item):
            #         raise ValueError("Plan item has incorrect format.")
            return data
        except json.JSONDecodeError as e_json:
            # Try ast.literal_eval as a fallback if json.loads fails
            try:
                evaluated_data = ast.literal_eval(json_str_cleaned)
                if not isinstance(evaluated_data, list):
                    raise ValueError(
                        "Fallback ast.literal_eval did not produce a list."
                    ) from e_json
                return evaluated_data
            except (
                Exception
            ) as e_ast:  # Catch any error from ast.literal_eval (SyntaxError, ValueError, etc.)
                # Re-raise the original json.JSONDecodeError if ast.literal_eval also fails or returns wrong type
                logger.warning(
                    "Failed to parse LLM plan response after multiple attempts",
                    content_preview=content[:500],
                )
                raise json.JSONDecodeError(
                    "Invalid JSON list in LLM response after all parsing attempts",
                    json_str_cleaned,
                    0,
                ) from e_ast

    # --------------------------- Public methods -----------------------------
    @retry_openai_llm
    async def generate_plan(
        self, goal_text: str, deadline_str: str, available_time_str: str
    ) -> List[dict[str, Any]]:
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
            f"Составь план достижения цели '{goal_text}' с дедлайном '{deadline_str}' "
            f"и ежедневным временем '{available_time_str}' в формате JSON"
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
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "Error processing LLM response",
                exc_info=e,
            )
            LLM_API_CALLS.labels(method_name=method_name, status="error").inc()
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
            f"Ты - мотивационный коуч. Пользователь работает над целью: {goal_text}. "
            f"Текущий прогресс: {progress_summary}. "
            f"Напиши вдохновляющее сообщение на русском из 2–3 коротких предложений (до 150 символов)."
        )
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

            # Try to parse as JSON first (in case LLM returns JSON despite not being asked to)
            try:
                json_content = json.loads(content)
                if isinstance(json_content, dict) and "message" in json_content:
                    content = json_content["message"]
                elif isinstance(json_content, str):
                    content = json_content
            except (json.JSONDecodeError, KeyError):
                # If not JSON or no 'message' key, use content as is
                pass

            LLM_API_CALLS.labels(method_name=method_name, status="success").inc()
            return content
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "Error processing LLM response",
                exc_info=e,
            )
            LLM_API_CALLS.labels(method_name=method_name, status="error").inc()
            raise
        finally:
            LLM_API_LATENCY.labels(method_name=method_name).observe(
                time.monotonic() - start_time
            )
