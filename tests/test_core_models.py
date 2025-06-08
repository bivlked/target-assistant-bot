"""Tests for core data models in core/models.py"""

import pytest
from core.models import (
    Goal,
    Task,
    GoalStatistics,
    GoalStatus,
    GoalPriority,
    TaskStatus,
)


class TestGoalStatus:
    """Test GoalStatus enum"""

    def test_goal_status_values(self):
        """Test GoalStatus enum values"""
        assert GoalStatus.ACTIVE.value == "активная"
        assert GoalStatus.COMPLETED.value == "завершенная"
        assert GoalStatus.ARCHIVED.value == "архивная"


class TestGoalPriority:
    """Test GoalPriority enum"""

    def test_goal_priority_values(self):
        """Test GoalPriority enum values"""
        assert GoalPriority.HIGH.value == "высокий"
        assert GoalPriority.MEDIUM.value == "средний"
        assert GoalPriority.LOW.value == "низкий"


class TestTaskStatus:
    """Test TaskStatus enum"""

    def test_task_status_values(self):
        """Test TaskStatus enum values"""
        assert TaskStatus.NOT_DONE.value == "Не выполнено"
        assert TaskStatus.DONE.value == "Выполнено"
        assert TaskStatus.PARTIALLY_DONE.value == "Частично выполнено"


class TestGoal:
    """Test Goal model"""

    def test_goal_creation(self):
        """Test basic Goal creation"""
        goal = Goal(
            goal_id=1,
            name="Test Goal",
            description="Test Description",
            deadline="2025-02-01",
            daily_time="1 hour",
            start_date="2025-01-01",
            status=GoalStatus.ACTIVE,
        )

        assert goal.goal_id == 1
        assert goal.name == "Test Goal"
        assert goal.status == GoalStatus.ACTIVE
        assert goal.priority == GoalPriority.MEDIUM  # default
        assert goal.tags == []  # default
        assert goal.progress_percent == 0  # default

    def test_goal_from_sheet_row_complete(self):
        """Test Goal creation from complete sheet row"""
        row = {
            "ID цели": "1",
            "Название цели": "Learn Python",
            "Глобальная цель": "Master programming",
            "Срок выполнения": "2025-03-01",
            "Затраты в день": "2 hours",
            "Начало выполнения": "2025-01-01",
            "Статус": "активная",
            "Приоритет": "высокий",
            "Теги": "programming, learning, python",
            "Прогресс (%)": "25",
            "Дата завершения": "2025-02-15",
        }

        goal = Goal.from_sheet_row(row)

        assert goal.goal_id == 1
        assert goal.name == "Learn Python"
        assert goal.description == "Master programming"
        assert goal.deadline == "2025-03-01"
        assert goal.daily_time == "2 hours"
        assert goal.start_date == "2025-01-01"
        assert goal.status == GoalStatus.ACTIVE
        assert goal.priority == GoalPriority.HIGH
        assert goal.tags == ["programming", "learning", "python"]
        assert goal.progress_percent == 25
        assert goal.completion_date == "2025-02-15"

    def test_goal_from_sheet_row_minimal(self):
        """Test Goal creation from minimal sheet row with defaults"""
        row = {}

        goal = Goal.from_sheet_row(row)

        assert goal.goal_id == 0
        assert goal.name == ""
        assert goal.description == ""
        assert goal.status == GoalStatus.ACTIVE
        assert goal.priority == GoalPriority.MEDIUM
        assert goal.tags == []
        assert goal.progress_percent == 0
        assert goal.completion_date is None

    def test_goal_from_sheet_row_invalid_priority(self):
        """Test Goal creation with invalid priority falls back to MEDIUM"""
        row = {"Приоритет": "invalid_priority"}

        goal = Goal.from_sheet_row(row)

        assert goal.priority == GoalPriority.MEDIUM

    def test_goal_from_sheet_row_empty_tags(self):
        """Test Goal creation with empty tags string"""
        row = {"Теги": ""}

        goal = Goal.from_sheet_row(row)

        assert goal.tags == []

    def test_goal_from_sheet_row_whitespace_tags(self):
        """Test Goal creation with whitespace-only tags"""
        row = {"Теги": " , , "}

        goal = Goal.from_sheet_row(row)

        assert goal.tags == []

    def test_goal_to_sheet_row(self):
        """Test Goal conversion to sheet row"""
        goal = Goal(
            goal_id=1,
            name="Test Goal",
            description="Test Description",
            deadline="2025-02-01",
            daily_time="1 hour",
            start_date="2025-01-01",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.HIGH,
            tags=["tag1", "tag2"],
            progress_percent=50,
            completion_date="2025-01-15",
        )

        row = goal.to_sheet_row()

        expected = [
            "1",
            "Test Goal",
            "Test Description",
            "2025-02-01",
            "1 hour",
            "2025-01-01",
            "активная",
            "высокий",
            "tag1, tag2",
            "50",
            "2025-01-15",
        ]

        assert row == expected

    def test_goal_to_sheet_row_no_completion_date(self):
        """Test Goal to sheet row with None completion date"""
        goal = Goal(
            goal_id=1,
            name="Test Goal",
            description="Test Description",
            deadline="2025-02-01",
            daily_time="1 hour",
            start_date="2025-01-01",
            status=GoalStatus.ACTIVE,
        )

        row = goal.to_sheet_row()

        # completion_date should be empty string when None
        assert row[-1] == ""


class TestTask:
    """Test Task model"""

    def test_task_creation(self):
        """Test basic Task creation"""
        task = Task(
            date="2025-01-15",
            day_of_week="Понедельник",
            task="Complete project",
            status=TaskStatus.NOT_DONE,
        )

        assert task.date == "2025-01-15"
        assert task.day_of_week == "Понедельник"
        assert task.task == "Complete project"
        assert task.status == TaskStatus.NOT_DONE
        assert task.goal_id is None
        assert task.goal_name is None

    def test_task_from_sheet_row(self):
        """Test Task creation from sheet row"""
        row = {
            "Дата": "2025-01-15",
            "День недели": "Понедельник",
            "Задача": "Learn Python",
            "Статус": "Выполнено",
        }

        task = Task.from_sheet_row(row, goal_id=1, goal_name="Programming Goal")

        assert task.date == "2025-01-15"
        assert task.day_of_week == "Понедельник"
        assert task.task == "Learn Python"
        assert task.status == TaskStatus.DONE
        assert task.goal_id == 1
        assert task.goal_name == "Programming Goal"

    def test_task_from_sheet_row_minimal(self):
        """Test Task creation from minimal sheet row"""
        row = {}

        task = Task.from_sheet_row(row)

        assert task.date == ""
        assert task.day_of_week == ""
        assert task.task == ""
        assert task.status == TaskStatus.NOT_DONE
        assert task.goal_id is None
        assert task.goal_name is None

    def test_task_to_sheet_row(self):
        """Test Task conversion to sheet row"""
        task = Task(
            date="2025-01-15",
            day_of_week="Понедельник",
            task="Complete project",
            status=TaskStatus.DONE,
        )

        row = task.to_sheet_row()

        expected = [
            "2025-01-15",
            "Понедельник",
            "Complete project",
            "Выполнено",
        ]

        assert row == expected


class TestGoalStatistics:
    """Test GoalStatistics model"""

    def test_goal_statistics_creation(self):
        """Test basic GoalStatistics creation"""
        stats = GoalStatistics(
            total_tasks=10,
            completed_tasks=7,
            progress_percent=70,
            days_elapsed=7,
            days_remaining=3,
            completion_rate=0.7,
        )

        assert stats.total_tasks == 10
        assert stats.completed_tasks == 7
        assert stats.progress_percent == 70
        assert stats.days_elapsed == 7
        assert stats.days_remaining == 3
        assert stats.completion_rate == 0.7
        assert stats.streak_days == 0  # default
        assert stats.best_streak == 0  # default

    def test_is_on_track_property_zero_days(self):
        """Test is_on_track property when days_elapsed is 0"""
        stats = GoalStatistics(
            total_tasks=10,
            completed_tasks=0,
            progress_percent=0,
            days_elapsed=0,
            days_remaining=10,
            completion_rate=0.0,
        )

        # Should be True when days_elapsed is 0
        assert stats.is_on_track is True

    def test_is_on_track_property_on_track(self):
        """Test is_on_track property when goal is on track"""
        stats = GoalStatistics(
            total_tasks=10,
            completed_tasks=5,
            progress_percent=50,
            days_elapsed=5,
            days_remaining=5,
            completion_rate=0.5,
        )

        # Expected progress: 50%, actual: 50% >= 45% (90% of expected)
        assert stats.is_on_track is True

    def test_is_on_track_property_behind_schedule(self):
        """Test is_on_track property when goal is behind schedule"""
        stats = GoalStatistics(
            total_tasks=10,
            completed_tasks=2,
            progress_percent=20,
            days_elapsed=8,
            days_remaining=2,
            completion_rate=0.2,
        )

        # Expected progress: 80%, actual: 20% < 72% (90% of expected)
        assert stats.is_on_track is False
