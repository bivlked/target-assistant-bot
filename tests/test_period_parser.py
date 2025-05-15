"""Tests for the period parsing utility (utils/period_parser.py), 
focusing on the heuristic part and overall logic.
"""

import pytest
from unittest.mock import patch

from utils.period_parser import (
    parse_period,
    _heuristic_days,
)  # Import _heuristic_days for direct testing

# from utils.period_parser import _llm_days # We will mock this one

# --- Tests for _heuristic_days ---


@pytest.mark.parametrize(
    "phrase, expected_days",
    [
        # Digits
        ("10 дней", 10),
        ("1 день", 1),
        ("45 дней", 45),
        ("0 дней", None),  # Should be handled as invalid by > 0 check
        ("-5 дней", None),  # Should be handled as invalid by > 0 check
        ("за 7 недель", 49),
        ("1 неделя", 7),
        ("6 недель", 42),
        ("две недели", 14),
        ("2 месяца", 60),
        ("1 месяц", 30),
        ("Полтора месяца", 45),  # 1.5 * 30
        (
            "1.5 недели",
            10,
        ),  # 1.5 * 7 = 10.5, rounds to 11 or 10? Let's check (round(10.5)=10)
        (
            "2,5 недели",
            18,
        ),  # 2.5 * 7 = 17.5, rounds to 18 or 17? (round(17.5)=18, so test should be 18)
        # Let's make it 18 as per round()
        # Russian word numbers
        ("три дня", 3),
        ("одна неделя", 7),
        ("два месяца", 60),
        ("десять недель", 70),
        # Implied 1
        ("неделя", 7),
        ("месяц", 30),
        ("день", 1),
        ("за месяц", 30),
        # Mixed cases
        ("через 3 недели", 21),
        ("в течение 1 месяца", 30),
        # No relevant keywords or numbers
        ("скоро", None),
        ("надолго", None),
        ("много времени", None),
    ],
)
def test_heuristic_days_parsing(phrase: str, expected_days: int | None):
    """Tests the _heuristic_days function with various inputs."""
    assert _heuristic_days(phrase) == expected_days


# --- Tests for parse_period (main function) ---


@patch("utils.period_parser._llm_days")  # Mock the LLM part
def test_parse_period_uses_heuristic_first(mock_llm_days):
    """Tests that parse_period tries heuristic first and uses its result if valid."""
    phrase = "за 2 недели"  # Should be parsed by heuristic
    expected_days = 14

    result = parse_period(phrase)

    assert result == expected_days
    mock_llm_days.assert_not_called()  # LLM should not be called


@patch("utils.period_parser._llm_days")
def test_parse_period_falls_back_to_llm(mock_llm_days):
    """Tests that parse_period falls back to LLM if heuristic fails."""
    phrase = "вечность"  # Heuristic should fail for this
    mock_llm_days.return_value = 100  # LLM successfully parses it

    result = parse_period(phrase)

    assert result == 100
    mock_llm_days.assert_called_once_with(phrase)


@patch("utils.period_parser._llm_days")
def test_parse_period_raises_value_error_if_all_fail(mock_llm_days):
    """Tests that parse_period raises ValueError if both heuristic and LLM fail."""
    phrase = "крайне неопределенно"
    mock_llm_days.return_value = None  # LLM also fails

    with pytest.raises(ValueError, match="Failed to parse the period."):
        parse_period(phrase)
    mock_llm_days.assert_called_once_with(phrase)


# Note: Tests for _llm_days itself (requiring OpenAI mock) should be in a separate
# file like test_period_parser_llm.py, which we already have.
