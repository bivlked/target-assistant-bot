import pytest

from utils import period_parser as pp


@pytest.mark.parametrize(
    ("text", "days_expected"),
    [
        ("6 недель", 42),
        ("две недели", 14),
        ("2 месяца", 60),
        ("45 дней", 45),
        ("день", 1),
        ("три дня", 3),
    ],
)
def test_parse_period_heuristic(text: str, days_expected: int, monkeypatch):
    # блокируем обращение к LLM, чтобы тесты не сетевые
    monkeypatch.setattr(pp, "_llm_days", lambda t: None)
    assert pp.parse_period(text) == days_expected


def test_parse_period_error(monkeypatch):
    monkeypatch.setattr(pp, "_llm_days", lambda t: None)
    with pytest.raises(ValueError):
        pp.parse_period("какой-то срок потом")
