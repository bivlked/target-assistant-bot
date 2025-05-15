"""Tests for the LLM-based period parsing functionality in utils.period_parser."""

import pytest
import json
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)  # Используем MagicMock для синхронного клиента
from typing import (
    Any,
    List,
    Dict,
    Optional,
)  # Добавляем List, Dict, Optional сюда, если они нужны для моков

from openai import APIError  # Используем из openai напрямую

from utils import period_parser  # Импортируем модуль для патчинга
from utils.period_parser import _llm_days  # Тестируемая функция


# --- Mocks for LLM responses ---
class MockLLMCompletionMessage:
    def __init__(self, content: str | None):
        self.content = content


class MockLLMChoice:
    def __init__(self, content: str | None):
        self.message = MockLLMCompletionMessage(content)


class MockLLMResponse:
    def __init__(self, choices: List[MockLLMChoice] | None = None):
        if choices is None:
            self.choices = []
        else:
            self.choices = choices


# --- Fixture for mocking _get_client ---
@pytest.fixture
def mock_openai_client(monkeypatch: pytest.MonkeyPatch):
    """Mocks the _get_client() function in period_parser to return a MagicMock client."""
    mock_client_instance = MagicMock()
    # Мокаем вложенный вызов completions.create
    mock_client_instance.chat.completions.create = (
        MagicMock()
    )  # Это будет наш основной mock для assertions

    monkeypatch.setattr(period_parser, "_get_client", lambda: mock_client_instance)
    return mock_client_instance


# --- Tests for _llm_days ---


def test_llm_days_success_direct_json(mock_openai_client: MagicMock):
    """_llm_days successfully parses a direct JSON response."""
    mock_openai_client.chat.completions.create.return_value = MockLLMResponse(
        choices=[MockLLMChoice('{"days": 42}')]
    )
    assert _llm_days("какой-то срок") == 42
    mock_openai_client.chat.completions.create.assert_called_once()


def test_llm_days_success_json_in_markdown(mock_openai_client: MagicMock):
    """_llm_days successfully parses JSON from a markdown code block."""
    # Эта логика теперь в _extract_plan, который вызывается из _llm_days, если JSON не прямой
    # Но _llm_days сам теперь не содержит re.search(r"{.*}"), он ожидает, что _extract_plan вернет объект
    # _llm_days ожидает, что chat.completions.create вернет JSON, и затем json.loads(m.group(0))
    # Значит, мы должны мокать ответ так, чтобы он содержал JSON, который json.loads сможет обработать.
    # _extract_plan в AsyncLLMClient теперь более сложный. _llm_days в period_parser имеет свой.
    # Текущий _llm_days в period_parser: re.search(r"{.*}", content) -> json.loads(m.group(0))
    mock_openai_client.chat.completions.create.return_value = MockLLMResponse(
        choices=[MockLLMChoice('Some text ```json\n{"days": 77}\n``` end text')]
    )
    assert _llm_days("еще срок") == 77


def test_llm_days_json_no_days_key(mock_openai_client: MagicMock):
    """_llm_days returns None if 'days' key is missing."""
    mock_openai_client.chat.completions.create.return_value = MockLLMResponse(
        choices=[MockLLMChoice('{"duration": 30}')]
    )
    assert _llm_days("срок без ключа days") is None


def test_llm_days_json_days_not_int(mock_openai_client: MagicMock):
    """_llm_days returns None if 'days' value is not an int."""
    mock_openai_client.chat.completions.create.return_value = MockLLMResponse(
        choices=[MockLLMChoice('{"days": "abc"}')]
    )
    assert _llm_days("срок с не-числом") is None


def test_llm_days_json_days_zero_or_negative(mock_openai_client: MagicMock):
    """_llm_days returns None if 'days' is 0 or negative."""
    mock_openai_client.chat.completions.create.return_value = MockLLMResponse(
        choices=[MockLLMChoice('{"days": 0}')]
    )
    assert _llm_days("нулевой срок") is None
    mock_openai_client.chat.completions.create.return_value = MockLLMResponse(
        choices=[MockLLMChoice('{"days": -5}')]
    )
    assert _llm_days("отрицательный срок") is None


def test_llm_days_malformed_json(mock_openai_client: MagicMock):
    """_llm_days returns None for malformed JSON."""
    mock_openai_client.chat.completions.create.return_value = MockLLMResponse(
        choices=[MockLLMChoice('{"days": 10')]
    )  # Missing closing brace
    assert _llm_days("плохой json") is None


def test_llm_days_no_json_in_response(mock_openai_client: MagicMock):
    """_llm_days returns None if no JSON object is found in the response."""
    mock_openai_client.chat.completions.create.return_value = MockLLMResponse(
        choices=[MockLLMChoice("Просто текст без JSON.")]
    )
    assert _llm_days("текст") is None


def test_llm_days_empty_choices(mock_openai_client: MagicMock):
    """_llm_days returns None if response.choices is empty."""
    mock_openai_client.chat.completions.create.return_value = MockLLMResponse(
        choices=[]
    )
    assert _llm_days("пустой choices") is None


def test_llm_days_message_content_none(mock_openai_client: MagicMock):
    """_llm_days returns None if message.content is None."""
    mock_openai_client.chat.completions.create.return_value = MockLLMResponse(
        choices=[MockLLMChoice(None)]
    )
    assert _llm_days("content is None") is None


@patch("utils.period_parser.logger.warning")  # Мокаем логгер
def test_llm_days_api_error_no_reraise(
    mock_logger_warning: MagicMock, mock_openai_client: MagicMock
):
    """_llm_days returns None and logs warning on APIError (due to @retry_openai_llm_no_reraise)."""
    # Декоратор @retry_openai_llm_no_reraise должен сделать 2 попытки
    mock_openai_client.chat.completions.create.side_effect = APIError(
        "Simulated API Error", request=MagicMock(), body=None
    )

    assert _llm_days("срок с API ошибкой") is None
    assert mock_openai_client.chat.completions.create.call_count == 2  # 2 attempts
    mock_logger_warning.assert_called()  # Проверяем, что была попытка логирования
    # Можно проверить и текст лога, если он специфичен для этой ситуации
