import pytest
from llm.client import LLMClient
from typing import List, Any


class DummyLLM(LLMClient):
    """Реализация LLMClient без сетевых вызовов."""

    def __init__(self, fake_response: str):
        # не вызываем super/__init__, чтобы OpenAI не инициализировался
        self._fake_response = fake_response

    # переопределяем приватный метод
    def _chat_completion(self, prompt: str) -> str:  # noqa: D401
        return self._fake_response

    # Override generate_plan to use the fake response directly for plan JSON
    def generate_plan(
        self, goal_text: str, deadline: str, time: str
    ) -> List[dict[str, Any]]:
        # In this dummy, assume _fake_response is already the plan JSON string
        # or can be processed by _extract_plan if it was set up for that.
        if self._fake_response.strip().startswith("["):
            # Attempt to parse it as if it's direct JSON or extractable
            return self._extract_plan(
                self._fake_response
            )  # Use existing extraction logic
        # Fallback or raise if _fake_response is not suitable for a plan
        raise ValueError(
            "DummyLLM._fake_response not set to a plan-like JSON string for generate_plan"
        )


PLAN_JSON = '[{"day": "01.05.25", "task": "T"}]'
PLAN_MD = f"""```json
{PLAN_JSON}
```"""
PLAN_TRAILING = '[{"day":"01.05.25","task":"T",},]'


@pytest.mark.parametrize(
    "content",
    [PLAN_JSON, PLAN_MD, PLAN_TRAILING],
)
def test_extract_plan(content):
    client = LLMClient()
    plan = client._extract_plan(content)
    assert isinstance(plan, list) and plan[0]["task"] == "T"


def test_generate_plan_happy(monkeypatch):
    dummy = DummyLLM(PLAN_JSON)
    plan = dummy.generate_plan("Goal", "05.05.25", "18:00")
    assert plan[0]["day"] == "01.05.25"


def test_generate_motivation(monkeypatch):
    txt = "You can do it!"
    dummy = DummyLLM(txt)
    mot = dummy.generate_motivation("Goal", "50% done")
    assert mot == txt
