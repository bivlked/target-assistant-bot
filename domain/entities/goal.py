"""
Goal Domain Entity

Core business entity representing a user goal with associated tasks.
Implements domain logic and business rules for goal management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from enum import Enum
import uuid

if TYPE_CHECKING:
    from domain.entities.task import Task


class GoalStatus(Enum):
    """Goal status enumeration"""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class GoalPriority(Enum):
    """Goal priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Goal:
    """
    Goal domain entity

    Represents a user's goal with business logic for progress calculation,
    status management, and task association.
    """

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: int = 0

    # Goal details
    title: str = ""
    description: Optional[str] = None
    status: GoalStatus = GoalStatus.DRAFT
    priority: GoalPriority = GoalPriority.MEDIUM

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Progress tracking
    tasks: List["Task"] = field(default_factory=list)
    target_value: Optional[float] = None
    current_value: float = 0.0
    unit: Optional[str] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization validation and setup"""
        if not self.title.strip():
            raise ValueError("Goal title cannot be empty")

        if self.user_id <= 0:
            raise ValueError("User ID must be positive")

        # Update timestamp
        self.updated_at = datetime.now()

        # Auto-start active goals
        if self.status == GoalStatus.ACTIVE and not self.started_at:
            self.started_at = datetime.now()

    def add_task(self, task: "Task") -> None:
        """
        Add task to goal

        Args:
            task: Task to add

        Raises:
            ValueError: If task is invalid or already exists
        """
        if not task.id:
            raise ValueError("Task must have valid ID")

        # Check for duplicate task IDs
        if any(t.id == task.id for t in self.tasks):
            raise ValueError(f"Task with ID {task.id} already exists")

        # Set goal reference
        task.goal_id = self.id

        # Add to tasks list
        self.tasks.append(task)

        # Update timestamp
        self.updated_at = datetime.now()

    def remove_task(self, task_id: str) -> bool:
        """
        Remove task from goal

        Args:
            task_id: ID of task to remove

        Returns:
            bool: True if task was removed, False if not found
        """
        original_count = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.id != task_id]

        if len(self.tasks) < original_count:
            self.updated_at = datetime.now()
            return True

        return False

    def get_task_by_id(self, task_id: str) -> Optional["Task"]:
        """Get task by ID"""
        return next((t for t in self.tasks if t.id == task_id), None)

    def calculate_progress(self) -> float:
        """
        Calculate goal completion percentage

        Returns:
            float: Progress percentage (0.0 to 100.0)
        """
        if self.target_value and self.target_value > 0:
            # Value-based progress
            return min((self.current_value / self.target_value) * 100, 100.0)

        if not self.tasks:
            return 0.0

        # Task-based progress
        completed_tasks = sum(1 for task in self.tasks if task.is_completed)
        return (completed_tasks / len(self.tasks)) * 100

    def get_completed_tasks(self) -> List["Task"]:
        """Get list of completed tasks"""
        return [task for task in self.tasks if task.is_completed]

    def get_pending_tasks(self) -> List["Task"]:
        """Get list of pending (incomplete) tasks"""
        return [task for task in self.tasks if not task.is_completed]

    def get_overdue_tasks(self) -> List["Task"]:
        """Get list of overdue tasks"""
        now = datetime.now()
        return [
            task
            for task in self.tasks
            if not task.is_completed and task.due_date and task.due_date < now
        ]

    def is_overdue(self) -> bool:
        """Check if goal is overdue"""
        return (
            self.deadline is not None
            and datetime.now() > self.deadline
            and self.status not in [GoalStatus.COMPLETED, GoalStatus.CANCELLED]
        )

    def is_completed(self) -> bool:
        """Check if goal is completed"""
        return self.status == GoalStatus.COMPLETED

    def mark_completed(self) -> None:
        """Mark goal as completed"""
        self.status = GoalStatus.COMPLETED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def mark_active(self) -> None:
        """Mark goal as active"""
        if self.status in [GoalStatus.COMPLETED, GoalStatus.CANCELLED]:
            raise ValueError("Cannot reactivate completed or cancelled goal")

        self.status = GoalStatus.ACTIVE

        if not self.started_at:
            self.started_at = datetime.now()

        self.updated_at = datetime.now()

    def pause(self) -> None:
        """Pause goal"""
        if self.status != GoalStatus.ACTIVE:
            raise ValueError("Can only pause active goals")

        self.status = GoalStatus.PAUSED
        self.updated_at = datetime.now()

    def cancel(self) -> None:
        """Cancel goal"""
        if self.status == GoalStatus.COMPLETED:
            raise ValueError("Cannot cancel completed goal")

        self.status = GoalStatus.CANCELLED
        self.updated_at = datetime.now()

    def add_progress(self, value: float) -> None:
        """
        Add to current progress value

        Args:
            value: Value to add to current progress
        """
        if value < 0:
            raise ValueError("Progress value cannot be negative")

        self.current_value += value
        self.updated_at = datetime.now()

        # Auto-complete if target reached
        if (
            self.target_value
            and self.current_value >= self.target_value
            and self.status == GoalStatus.ACTIVE
        ):
            self.mark_completed()

    def set_progress(self, value: float) -> None:
        """
        Set current progress value

        Args:
            value: New progress value
        """
        if value < 0:
            raise ValueError("Progress value cannot be negative")

        self.current_value = value
        self.updated_at = datetime.now()

        # Auto-complete if target reached
        if (
            self.target_value
            and self.current_value >= self.target_value
            and self.status == GoalStatus.ACTIVE
        ):
            self.mark_completed()

    def get_days_until_deadline(self) -> Optional[int]:
        """
        Get number of days until deadline

        Returns:
            Optional[int]: Days until deadline, None if no deadline
        """
        if not self.deadline:
            return None

        delta = self.deadline - datetime.now()
        return delta.days

    def get_time_spent(self) -> Optional[int]:
        """
        Get time spent on goal in days

        Returns:
            Optional[int]: Days since goal started, None if not started
        """
        if not self.started_at:
            return None

        delta = datetime.now() - self.started_at
        return delta.days

    def add_tag(self, tag: str) -> None:
        """Add tag to goal"""
        tag = tag.strip().lower()
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()

    def remove_tag(self, tag: str) -> bool:
        """Remove tag from goal"""
        tag = tag.strip().lower()
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
            return True
        return False

    def has_tag(self, tag: str) -> bool:
        """Check if goal has specific tag"""
        return tag.strip().lower() in self.tags

    def to_dict(self) -> Dict[str, Any]:
        """Convert goal to dictionary representation"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "target_value": self.target_value,
            "current_value": self.current_value,
            "unit": self.unit,
            "tags": self.tags,
            "metadata": self.metadata,
            "progress": self.calculate_progress(),
            "tasks_count": len(self.tasks),
            "completed_tasks_count": len(self.get_completed_tasks()),
            "is_overdue": self.is_overdue(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goal":
        """Create goal from dictionary representation"""
        goal = cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", 0),
            title=data.get("title", ""),
            description=data.get("description"),
            status=GoalStatus(data.get("status", "draft")),
            priority=GoalPriority(data.get("priority", "medium")),
            target_value=data.get("target_value"),
            current_value=data.get("current_value", 0.0),
            unit=data.get("unit"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

        # Set timestamps if provided
        if "created_at" in data:
            goal.created_at = datetime.fromisoformat(data["created_at"])

        if "updated_at" in data:
            goal.updated_at = datetime.fromisoformat(data["updated_at"])

        if data.get("deadline"):
            goal.deadline = datetime.fromisoformat(data["deadline"])

        if data.get("started_at"):
            goal.started_at = datetime.fromisoformat(data["started_at"])

        if data.get("completed_at"):
            goal.completed_at = datetime.fromisoformat(data["completed_at"])

        return goal

    def __repr__(self) -> str:
        """String representation of goal"""
        return f"Goal(id='{self.id}', title='{self.title}', status='{self.status.value}', progress={self.calculate_progress():.1f}%)"

    def __eq__(self, other) -> bool:
        """Equality comparison based on ID"""
        if not isinstance(other, Goal):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID"""
        return hash(self.id)
