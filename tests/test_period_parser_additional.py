import pytest

from utils import period_parser


def test_parse_period_raises_when_unrecognized(monkeypatch):
    # Эвристика вернёт None, LLM мы подменяем, чтобы тоже вернуть None
    monkeypatch.setattr(period_parser, "_llm_days", lambda text: None, raising=True)

    with pytest.raises(ValueError):
        period_parser.parse_period("когда-нибудь потом")
