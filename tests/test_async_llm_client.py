"""Tests for the asynchronous LLM client (llm.async_client.AsyncLLMClient)."""

import pytest
import json  # For json.JSONDecodeError
from llm.async_client import AsyncLLMClient
from typing import Any, List, Dict  # Добавил Dict для единообразия
from unittest.mock import AsyncMock, patch, MagicMock  # Добавил MagicMock
from openai import APIError  # Добавил APIError

# --- Tests for _extract_plan ---


@pytest.mark.parametrize(
    "content, expected_result_or_task_in_first_item, expected_exception",
    [
        # Happy paths
        (
            '[{"day": 1, "task": "Task One"}, {"day": 2, "task": "Task Two"}]',
            "Task One",
            None,
        ),
        ('```json\n[{"day": 1, "task": "Markdown Task"}]\n```', "Markdown Task", None),
        ('```\n[{"day": 1, "task": "Simple MD Task"}]\n```', "Simple MD Task", None),
        (
            'Some intro text [{"day": 1, "task": "Text Around"}] some concluding text',
            "Text Around",
            None,
        ),
        ("[]", [], None),  # Empty list should parse to empty list
        ('[{"day": 1, "task": "Trailing Comma Fixed"},]', "Trailing Comma Fixed", None),
        ("[{'day': 1, 'task': 'Single Quotes'}]", "Single Quotes", None),
        ("[{'day': 1, 'task': 'Single Quotes Trail'},]", "Single Quotes Trail", None),
        (
            '[{"day":1, "task":"NoSpace"},{"day" : 2, "task" : "Spaces around colons"}]',
            "NoSpace",
            None,
        ),  # Test spacing variations
        (
            'Leading text\n```json\n[{"day": 1, "task": "MD with text"}]\n```\nTrailing text',
            "MD with text",
            None,
        ),
        # Error cases - Adjusted expectation for strings that ast.literal_eval might parse
        # Если _extract_plan с ast.literal_eval успешно парсит 'Bad JSON\'}', то исключения не будет.
        # Давайте сделаем строку точно невалидной для обоих.
        (
            '[{"day": 1, "task": "Bad JSON\'"}',
            None,
            json.JSONDecodeError,
        ),  # Ошибка в кавычках, невалидно для json.loads и ast.literal_eval
        ('{"object": true}', None, ValueError),
        ("Completely irrelevant text", None, ValueError),
    ],
)
def test_async_extract_plan(
    content: str,
    expected_result_or_task_in_first_item: Any,
    expected_exception: type[Exception] | None,
):
    """Tests the static _extract_plan method for various LLM response formats."""
    if expected_exception:
        with pytest.raises(expected_exception):
            AsyncLLMClient._extract_plan(content)
    else:
        plan = AsyncLLMClient._extract_plan(content)
        assert isinstance(plan, list)
        if isinstance(expected_result_or_task_in_first_item, list):
            assert plan == expected_result_or_task_in_first_item
        elif expected_result_or_task_in_first_item is not None:
            assert len(plan) > 0, f"Expected non-empty plan, got {plan}"
            assert isinstance(
                plan[0], dict
            ), f"Expected first item to be dict, got {type(plan[0])}"
            assert plan[0].get("task") == expected_result_or_task_in_first_item
        # If expected_result_or_task_in_first_item is None and no exception, it might mean empty list successfully parsed.
        # This is covered by `('[]', [], None)`.


# --- Mocks for AsyncLLMClient tests ---
class MockAsyncChatCompletionMessage:
    def __init__(self, content: str):
        self.content = content


class MockAsyncChoice:
    def __init__(self, content: str):
        self.message = MockAsyncChatCompletionMessage(content)


class MockAsyncChatCompletion:
    def __init__(
        self, content: str = "[]"
    ):  # По умолчанию возвращаем пустой JSON-список
        self.choices = [MockAsyncChoice(content)]


# --- Tests for AsyncLLMClient public methods ---


@pytest.mark.asyncio
async def test_generate_plan_success(monkeypatch: pytest.MonkeyPatch):
    """Tests AsyncLLMClient.generate_plan on successful API call and plan extraction."""
    mock_openai_create = AsyncMock(
        return_value=MockAsyncChatCompletion('[{"day": 1, "task": "Test plan task"}]')
    )

    # Патчим метод create у экземпляра клиента OpenAI внутри AsyncLLMClient
    # Это требует, чтобы AsyncLLMClient создавал свой self.client в __init__
    # и мы могли его запатчить после создания экземпляра AsyncLLMClient

    client = AsyncLLMClient()  # Создаем экземпляр
    monkeypatch.setattr(client.client.chat.completions, "create", mock_openai_create)

    plan = await client.generate_plan("Test Goal", "1 week", "1 hour")

    assert len(plan) == 1
    assert plan[0]["task"] == "Test plan task"
    mock_openai_create.assert_awaited_once()  # Проверяем, что API был вызван
    # TODO: Добавить ассерты на аргументы вызова mock_openai_create (model, messages, etc.)


@pytest.mark.asyncio
async def test_generate_plan_api_error(monkeypatch: pytest.MonkeyPatch):
    """Tests AsyncLLMClient.generate_plan when API call raises an error (after retries)."""
    # Мок для @retry_openai_llm, чтобы он не делал реальных повторов, а сразу выбрасывал ошибку
    # Или можно настроить mock_openai_create, чтобы он выбрасывал APIError,
    # а декоратор @retry_openai_llm должен это обработать.
    # Для простоты, сначала проверим без глубокого тестирования самого retry декоратора здесь.
    mock_openai_create = AsyncMock(
        side_effect=APIError("Test API Error", request=MagicMock(), body=None)
    )

    client = AsyncLLMClient()
    monkeypatch.setattr(client.client.chat.completions, "create", mock_openai_create)

    with pytest.raises(APIError):
        await client.generate_plan("Error Goal", "1 day", "1 hour")

    # Убедимся, что попытка вызова была (декоратор @retry_openai_llm должен обеспечить несколько попыток)
    # Точное количество вызовов зависит от настроек @retry_openai_llm
    assert mock_openai_create.call_count >= 1


@pytest.mark.asyncio
async def test_generate_plan_bad_json(monkeypatch: pytest.MonkeyPatch):
    """Tests AsyncLLMClient.generate_plan when LLM returns malformed JSON."""
    mock_openai_create = AsyncMock(
        return_value=MockAsyncChatCompletion("not a json list at all")
    )
    client = AsyncLLMClient()
    monkeypatch.setattr(client.client.chat.completions, "create", mock_openai_create)

    with pytest.raises(
        ValueError
    ):  # _extract_plan должен выбросить ValueError или json.JSONDecodeError
        await client.generate_plan("Bad JSON Goal", "2 days", "2 hours")


# --- Tests for generate_motivation ---


@pytest.mark.asyncio
async def test_generate_motivation_success(monkeypatch: pytest.MonkeyPatch):
    """Tests AsyncLLMClient.generate_motivation on successful API call."""
    expected_motivation = "You are doing great!"
    mock_openai_create = AsyncMock(
        return_value=MockAsyncChatCompletion(expected_motivation)
    )

    client = AsyncLLMClient()
    monkeypatch.setattr(client.client.chat.completions, "create", mock_openai_create)

    motivation = await client.generate_motivation(
        "Test Goal for Motivation", "50% progress"
    )

    assert motivation == expected_motivation
    mock_openai_create.assert_awaited_once()
    # TODO: Add asserts for arguments of mock_openai_create


@pytest.mark.asyncio
async def test_generate_motivation_api_error(monkeypatch: pytest.MonkeyPatch):
    """Tests AsyncLLMClient.generate_motivation when API call raises an error."""
    mock_openai_create = AsyncMock(
        side_effect=APIError(
            "Test API Error for Motivation", request=MagicMock(), body=None
        )
    )

    client = AsyncLLMClient()
    monkeypatch.setattr(client.client.chat.completions, "create", mock_openai_create)

    with pytest.raises(APIError):
        await client.generate_motivation("Error Goal Motivation", "10% progress")

    assert mock_openai_create.call_count >= 1  # Due to @retry_openai_llm
