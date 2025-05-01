import importlib

import pytest

import utils.period_parser as pp
from handlers.goal_setting import _validate_deadline
from config import _int_env


@pytest.mark.parametrize(
    "phrase, expected",
    [
        ("за 3 недели", 21),
        ("четыре месяца", 120),
        ("10 дней", 10),
        ("месяц", 30),
        ("неделя", 7),
    ],
)
def test_heuristic_days(phrase, expected):
    assert pp._heuristic_days(phrase) == expected


@pytest.mark.parametrize(
    "phrase, is_valid",
    [
        ("за 3 недели", True),
        ("за 2 месяца", True),
        ("неделя", True),
        ("4 месяца", False),  # 120 дней
        ("91 день", False),
    ],
)
def test_validate_deadline(phrase, is_valid):
    assert _validate_deadline(phrase) is is_valid


def test_int_env(monkeypatch):
    # корректное число
    monkeypatch.setenv("TEST_INT", "  42px")
    assert _int_env("TEST_INT", 0) == 42
    # отсутствие переменной -> default
    monkeypatch.delenv("TEST_INT", raising=False)
    assert _int_env("TEST_INT", 5) == 5
    # некорректное содержимое -> default
    monkeypatch.setenv("TEST_INT", "abc")
    assert _int_env("TEST_INT", 7) == 7
