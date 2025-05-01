import pytest

from utils.period_parser import parse_period


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("за 3 недели", 21),
        ("за 2 месяца", 60),
        ("за 10 дней", 10),
        ("месяц", 30),  # без числа, подразумеваем 1 месяц
    ],
)
def test_parse_period_heuristic_success(phrase, expected):
    assert parse_period(phrase) == expected
