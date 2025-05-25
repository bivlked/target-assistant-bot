import pytest
import utils.period_parser as pp

# from handlers.goal_setting import _validate_deadline # Removed import
# from config import _int_env # _int_env and its test moved to test_config.py


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


# test_int_env was here and has been moved to tests/test_config.py
