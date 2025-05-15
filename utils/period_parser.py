from __future__ import annotations

"""Parses a user-provided phrase representing a period (e.g., "for a month", "6 weeks", "45 days").
It first attempts to parse heuristically, then falls back to an LLM query if needed.
Returns the number of days (int). Raises ValueError if parsing fails.
"""
from typing import Optional
import logging
import json
import re

from openai import OpenAI, APIError

from config import openai_cfg
from utils.retry_decorators import retry_openai_llm_no_reraise

logger = logging.getLogger(__name__)

# Word-based numbers in Russian (up to 10 is sufficient for typical inputs)
_WORDS_MAP = {
    "ноль": 0,
    "один": 1,
    "одна": 1,
    "полтора": 1.5,
    "полторы": 1.5,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
}


# ---------------------------------------------------------------------------
# Heuristic parser (fast, no network calls)
# ---------------------------------------------------------------------------


def _heuristic_days(text: str) -> Optional[int]:
    """Heuristically parses a text string to extract the number of days.

    Handles numbers in digits, numbers as Russian words, and common period units.
    Assumes 1 if a unit (month/week/day) is present without an explicit number.

    Args:
        text: The input text string from the user.

    Returns:
        The number of days as an integer, or None if parsing fails.
    """
    txt = text.lower()

    # 1. Number specified in digits
    num_match = re.search(r"([-+]?\d+[\,\.\d]*)", txt)
    if num_match:
        try:
            num = float(num_match.group(1).replace(",", "."))
        except Exception:
            num = None
    else:
        # 2. Number specified as a word
        num = None
        for w, val in _WORDS_MAP.items():
            if re.search(rf"\b{w}\b", txt):
                num = val
                break
        # 3. If no number is found but a keyword is present, assume 1
        if num is None and ("месяц" in txt or "недел" in txt or "день" in txt):
            num = 1

    if num is None:
        return None

    # Unit of measurement
    if "нед" in txt:
        days = int(round(num * 7))
    elif "месяц" in txt or "мес" in txt:
        days = int(round(num * 30))
    else:
        # Default to days
        days = int(round(num))

    return days if days > 0 else None


# ---------------------------------------------------------------------------
# LLM parser (fallback). Max 1 request if heuristic parsing fails.
# ---------------------------------------------------------------------------

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """(Internal) Initializes and returns the OpenAI client singleton."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=openai_cfg.api_key)
    return _client


@retry_openai_llm_no_reraise
def _llm_days(text: str) -> Optional[int]:
    """Asks the LLM how many days the phrase contains. Returns int or None."""
    prompt = (
        "Определи количество календарных дней, содержащихся во фразе на русском языке. "  # Russian prompt for LLM
        'Ответь ТОЛЬКО JSON формата {"days": <число>} без пояснений.\n\n'
        f'Фраза: "{text}"'
    )
    try:
        response = _get_client().chat.completions.create(
            model=openai_cfg.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=5,  # seconds
        )
        # OpenAI may theoretically return empty choices or message without content.
        # Added explicit defensive checks to avoid AttributeError at runtime and
        # allow static analyzers (mypy) to see that `content` is always a `str`.

        if not response.choices:  # pragma: no cover – extremely rare but handled
            return None

        raw = response.choices[0].message.content
        if raw is None:
            return None

        content = raw.strip()
        logger.debug("LLM period raw response: %s", content)

        # Try to extract JSON structure from the response.
        m = re.search(r"{.*}", content)
        if not m:
            return None

        data = json.loads(m.group(0))
        days_val_raw = data.get("days")
        if days_val_raw is None:
            logger.debug("'days' key not found in LLM JSON response.")
            return None
        days_val = int(days_val_raw)
        return days_val if days_val > 0 else None
    except (APIError, json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        logger.warning("LLM parse period failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def parse_period(text: str) -> int:
    """Returns the number of days. Raises ValueError on failure."""
    days = _heuristic_days(text)
    if days is None:
        days = _llm_days(text)
    if days is None:
        raise ValueError("Failed to parse the period.")  # Translated error message
    return days
