from __future__ import annotations

"""Парсер пользовательской фразы со сроком («за месяц», «6 недель», «45 дней» ...).
Сначала пытаемся разобрать эвристически, затем (при неудаче) спрашиваем LLM.
Возвращает количество дней (int). Если распознать не удалось — ValueError.
"""
from typing import Optional
import logging
import json
import re

from tenacity import retry, wait_exponential, stop_after_attempt
from openai import OpenAI, APIError

from config import openai_cfg

logger = logging.getLogger(__name__)

# Словесные числа для русского языка (до 10 достаточно)
_WORDS_MAP = {
    "ноль": 0,
    "один": 1,
    "одна": 1,
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
# Эвристический парсер (быстрый, без сети)
# ---------------------------------------------------------------------------

def _heuristic_days(text: str) -> Optional[int]:
    txt = text.lower()

    # 1. Указано число цифрой
    num_match = re.search(r"(\d+[\,\.\d]*)", txt)
    if num_match:
        try:
            num = float(num_match.group(1).replace(",", "."))
        except Exception:
            num = None
    else:
        # 2. Словесное число
        num = None
        for w, val in _WORDS_MAP.items():
            if re.search(fr"\b{w}\b", txt):
                num = val
                break
        # 3. Если число не найдено и присутствует ключевое слово — считаем 1
        if num is None and ("месяц" in txt or "недел" in txt or "день" in txt):
            num = 1

    if num is None:
        return None

    # Единица измерения
    if "нед" in txt:
        days = int(round(num * 7))
    elif "месяц" in txt or "мес" in txt:
        days = int(round(num * 30))
    else:
        # По умолчанию дни
        days = int(round(num))

    return days if days > 0 else None


# ---------------------------------------------------------------------------
# LLM-парсер (fallback). Максимум 1 запрос при ошибке эвристики.
# ---------------------------------------------------------------------------

_client: Optional[OpenAI] = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=openai_cfg.api_key)
    return _client


@retry(wait=wait_exponential(multiplier=1, min=1, max=4), stop=stop_after_attempt(2), reraise=False)
def _llm_days(text: str) -> Optional[int]:
    """Спросить у LLM сколько дней содержит фраза. Возвращает int или None."""
    prompt = (
        "Определи количество календарных дней, содержащихся во фразе на русском языке. "
        "Ответь ТОЛЬКО JSON формата {\"days\": <число>} без пояснений.\n\n"
        f"Фраза: \"{text}\""
    )
    try:
        response = _get_client().chat.completions.create(
            model=openai_cfg.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=5,  # секунд
        )
        content = response.choices[0].message.content.strip()
        logger.debug("LLM period raw response: %s", content)
        # Пытаемся извлечь JSON
        m = re.search(r"{.*}", content)
        if not m:
            return None
        data = json.loads(m.group(0))
        days_val = int(data.get("days"))
        return days_val if days_val > 0 else None
    except (APIError, json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning("LLM parse period failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Публичная функция
# ---------------------------------------------------------------------------

def parse_period(text: str) -> int:
    """Возвращает количество дней. Бросает ValueError при неудаче."""
    days = _heuristic_days(text)
    if days is None:
        days = _llm_days(text)
    if days is None:
        raise ValueError("Не удалось распознать срок.")
    return days 