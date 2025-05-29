"""Data models for Target Assistant Bot."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class GoalStatus(Enum):
    """Goal statuses."""

    ACTIVE = "активная"
    COMPLETED = "завершенная"
    ARCHIVED = "архивная"


class GoalPriority(Enum):
    """Goal priorities."""

    HIGH = "высокий"
    MEDIUM = "средний"
    LOW = "низкий"


class TaskStatus(Enum):
    """Task statuses."""

    NOT_DONE = "Не выполнено"
    DONE = "Выполнено"
    PARTIALLY_DONE = "Частично выполнено"


@dataclass
class Goal:
    """Goal model."""

    goal_id: int
    name: str
    description: str
    deadline: str
    daily_time: str
    start_date: str
    status: GoalStatus
    priority: GoalPriority = GoalPriority.MEDIUM
    tags: List[str] = field(default_factory=list)
    progress_percent: int = 0
    completion_date: Optional[str] = None

    @classmethod
    def from_sheet_row(cls, row: Dict[str, Any]) -> Goal:
        """Create Goal object from Google Sheets row."""
        # Parse tags from comma-separated string
        tags_str = row.get("Теги", "")
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

        # Parse priority with fallback to MEDIUM
        priority_str = row.get("Приоритет", GoalPriority.MEDIUM.value)
        try:
            priority = GoalPriority(priority_str)
        except ValueError:
            priority = GoalPriority.MEDIUM

        return cls(
            goal_id=int(row.get("ID цели", 0)),
            name=row.get("Название цели", ""),
            description=row.get("Глобальная цель", ""),
            deadline=row.get("Срок выполнения", ""),
            daily_time=row.get("Затраты в день", ""),
            start_date=row.get("Начало выполнения", ""),
            status=GoalStatus(row.get("Статус", GoalStatus.ACTIVE.value)),
            priority=priority,
            tags=tags,
            progress_percent=int(row.get("Прогресс (%)", 0)),
            completion_date=row.get("Дата завершения"),
        )

    def to_sheet_row(self) -> List[Any]:
        """Convert object to row for Google Sheets."""
        return [
            str(self.goal_id),
            self.name,
            self.description,
            self.deadline,
            self.daily_time,
            self.start_date,
            self.status.value,
            self.priority.value,
            ", ".join(self.tags),
            str(self.progress_percent),
            self.completion_date or "",
        ]


@dataclass
class Task:
    """Task model."""

    date: str
    day_of_week: str
    task: str
    status: TaskStatus
    goal_id: Optional[int] = None
    goal_name: Optional[str] = None

    @classmethod
    def from_sheet_row(
        cls,
        row: Dict[str, Any],
        goal_id: Optional[int] = None,
        goal_name: Optional[str] = None,
    ) -> Task:
        """Create Task object from Google Sheets row."""
        return cls(
            date=row.get("Дата", ""),
            day_of_week=row.get("День недели", ""),
            task=row.get("Задача", ""),
            status=TaskStatus(row.get("Статус", TaskStatus.NOT_DONE.value)),
            goal_id=goal_id,
            goal_name=goal_name,
        )

    def to_sheet_row(self) -> List[Any]:
        """Convert task to sheet row."""
        return [
            self.date,
            self.day_of_week,
            self.task,
            self.status.value,
        ]


@dataclass
class GoalStatistics:
    """Statistics for a goal."""

    total_tasks: int
    completed_tasks: int
    progress_percent: int
    days_elapsed: int
    days_remaining: int
    completion_rate: float
    streak_days: int = 0
    best_streak: int = 0

    @property
    def is_on_track(self) -> bool:
        """Check if goal is on track based on progress and time."""
        if self.days_elapsed == 0:
            return True
        expected_progress = (
            self.days_elapsed / (self.days_elapsed + self.days_remaining)
        ) * 100
        return (
            self.progress_percent >= expected_progress * 0.9
        )  # 90% of expected progress
