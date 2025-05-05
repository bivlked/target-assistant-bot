import pytest
from llm.client import LLMClient


class DummyLLM(LLMClient):
    """Реализация LLMClient без сетевых вызовов."""

    def __init__(self, fake_response: str):
        # не вызываем super/__init__, чтобы OpenAI не инициализировался
        self._fake_response = fake_response

    # переопределяем приватный метод
    def _chat_completion(self, prompt: str) -> str:  # noqa: D401
        return self._fake_response


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
