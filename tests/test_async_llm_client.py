"""Tests for the asynchronous LLM client (llm.async_client.AsyncLLMClient)."""

import pytest
import json  # For json.JSONDecodeError
from llm.async_client import AsyncLLMClient
from typing import Any  # Добавил Dict для единообразия
from unittest.mock import AsyncMock, MagicMock, patch  # Добавил MagicMock
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
        return_value=MockAsyncChatCompletion(
            '{"tasks": [{"day_number": 1, "task": "Test plan task"}]}'
        )
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

    # Enhanced assertions for call arguments (resolves TODO comment)
    call_args = mock_openai_create.await_args
    assert call_args is not None
    assert call_args.kwargs["model"] == client.model
    assert len(call_args.kwargs["messages"]) == 2
    assert call_args.kwargs["messages"][0]["role"] == "system"
    assert call_args.kwargs["messages"][1]["role"] == "user"
    assert call_args.kwargs["temperature"] == 0.7
    assert call_args.kwargs["response_format"] == {"type": "json_object"}
    assert "Test Goal" in call_args.kwargs["messages"][1]["content"]
    assert "1 week" in call_args.kwargs["messages"][1]["content"]
    assert "1 hour" in call_args.kwargs["messages"][1]["content"]


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


@pytest.mark.asyncio
async def test_generate_plan_malformed_json_fallback(monkeypatch: pytest.MonkeyPatch):
    """Tests generate_plan when LLM returns malformed JSON that triggers fallback to _extract_plan."""
    mock_openai_create = AsyncMock(
        return_value=MockAsyncChatCompletion('{"malformed": "not_tasks_key"}')
    )

    client = AsyncLLMClient()
    monkeypatch.setattr(client.client.chat.completions, "create", mock_openai_create)

    # Mock _extract_plan to return a valid plan when called as fallback
    expected_fallback_plan = [{"day_number": 1, "task": "Fallback task"}]
    monkeypatch.setattr(client, "_extract_plan", lambda content: expected_fallback_plan)

    plan = await client.generate_plan("Fallback Goal", "2 days", "30 minutes")

    assert plan == expected_fallback_plan
    mock_openai_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_plan_json_decode_error_coverage(
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests generate_plan when LLM returns completely invalid JSON (covers lines 160-163)."""
    mock_openai_create = AsyncMock(
        return_value=MockAsyncChatCompletion("invalid json content { malformed")
    )

    client = AsyncLLMClient()
    monkeypatch.setattr(client.client.chat.completions, "create", mock_openai_create)

    with pytest.raises(json.JSONDecodeError):
        await client.generate_plan("Error Goal", "1 day", "1 hour")


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

    # Enhanced assertions for call arguments (resolves TODO comment)
    call_args = mock_openai_create.await_args
    assert call_args is not None
    assert call_args.kwargs["model"] == client.model
    assert len(call_args.kwargs["messages"]) == 2
    assert call_args.kwargs["messages"][0]["role"] == "system"
    assert call_args.kwargs["messages"][1]["role"] == "user"
    assert call_args.kwargs["temperature"] == 0.7
    assert "Test Goal for Motivation" in call_args.kwargs["messages"][1]["content"]
    assert "50% progress" in call_args.kwargs["messages"][1]["content"]


@pytest.mark.asyncio
async def test_generate_motivation_json_response_with_message_key(
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests generate_motivation when LLM returns JSON with 'message' key (covers lines 221-224)."""
    expected_motivation = "Keep going strong!"
    json_response = f'{{"message": "{expected_motivation}"}}'
    mock_openai_create = AsyncMock(return_value=MockAsyncChatCompletion(json_response))

    client = AsyncLLMClient()
    monkeypatch.setattr(client.client.chat.completions, "create", mock_openai_create)

    motivation = await client.generate_motivation("JSON Goal", "75% progress")

    assert motivation == expected_motivation
    mock_openai_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_motivation_json_string_response(
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests generate_motivation when LLM returns JSON string (covers lines 231-237)."""
    expected_motivation = "Almost there!"
    json_response = f'"{expected_motivation}"'
    mock_openai_create = AsyncMock(return_value=MockAsyncChatCompletion(json_response))

    client = AsyncLLMClient()
    monkeypatch.setattr(client.client.chat.completions, "create", mock_openai_create)

    motivation = await client.generate_motivation("String Goal", "90% progress")

    assert motivation == expected_motivation
    mock_openai_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_motivation_json_decode_error_coverage(
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests generate_motivation when LLM returns invalid JSON that triggers fallback (covers error handling)."""
    invalid_json_response = "This is not JSON but still a valid motivation message"
    mock_openai_create = AsyncMock(
        return_value=MockAsyncChatCompletion(invalid_json_response)
    )

    client = AsyncLLMClient()
    monkeypatch.setattr(client.client.chat.completions, "create", mock_openai_create)

    motivation = await client.generate_motivation("Fallback Goal", "60% progress")

    # Should use the content as-is when JSON parsing fails
    assert motivation == invalid_json_response
    mock_openai_create.assert_awaited_once()


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


def test_extract_plan_logger_warning_coverage():
    """Tests _extract_plan when it logs warning before raising exception (covers line 85)."""
    invalid_content = "completely invalid content that cannot be parsed"

    with patch("llm.async_client.logger.warning") as mock_warning:
        with pytest.raises(json.JSONDecodeError):
            AsyncLLMClient._extract_plan(invalid_content)

        # Verify that warning was logged with content preview
        mock_warning.assert_called_once()
        call_args = mock_warning.call_args
        assert "Failed to parse LLM plan response" in str(call_args)
        assert "content_preview" in call_args.kwargs
