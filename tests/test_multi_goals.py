"""Tests for multi-goal functionality."""

import pytest
from unittest.mock import AsyncMock

from core.models import Goal, GoalPriority, GoalStatus, Task, TaskStatus


def test_goal_creation():
    """Test goal creation."""
    goal = Goal(
        goal_id=1,
        name="Test Goal",
        description="Learn Python programming",
        deadline="3 months",
        daily_time="1 hour",
        start_date="01.01.2024",
        status=GoalStatus.ACTIVE,
        priority=GoalPriority.HIGH,
        tags=["programming", "learning"],
        progress_percent=50,
    )

    assert goal.goal_id == 1
    assert goal.name == "Test Goal"
    assert goal.status == GoalStatus.ACTIVE
    assert goal.priority == GoalPriority.HIGH
    assert len(goal.tags) == 2


def test_task_creation():
    """Test task creation."""
    task = Task(
        date="01.01.2024",
        day_of_week="Monday",
        task="Study Python basics",
        status=TaskStatus.NOT_DONE,
        goal_id=1,
        goal_name="Test Goal",
    )

    assert task.goal_id == 1
    assert task.goal_name == "Test Goal"
    assert task.status == TaskStatus.NOT_DONE
    assert task.task == "Study Python basics"


def test_goal_from_sheet_row():
    """Test creating goal from sheet row."""
    row = {
        "ID цели": "1",
        "Название цели": "Test Goal",
        "Глобальная цель": "Learn Python programming",
        "Срок выполнения": "3 months",
        "Затраты в день": "1 hour",
        "Начало выполнения": "01.01.2024",
        "Статус": "активная",
        "Приоритет": "высокий",
        "Теги": "programming, learning",
        "Прогресс (%)": "50",
        "Дата завершения": "",
    }

    goal = Goal.from_sheet_row(row)

    assert goal.goal_id == 1
    assert goal.name == "Test Goal"
    assert goal.status == GoalStatus.ACTIVE
    assert goal.priority == GoalPriority.HIGH
    assert goal.tags == ["programming", "learning"]
    assert goal.progress_percent == 50


def test_dependency_injection():
    """Test dependency injection."""
    from core.dependency_injection import (
        initialize_dependencies,
        get_async_storage,
        get_async_llm,
    )

    # Create mocks
    mock_storage = AsyncMock()
    mock_llm = AsyncMock()

    # Initialize
    initialize_dependencies(mock_storage, mock_llm)

    # Test retrieval
    storage = get_async_storage()
    llm = get_async_llm()

    assert storage is mock_storage
    assert llm is mock_llm
