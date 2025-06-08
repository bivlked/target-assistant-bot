"""
Task Domain Entity

Core business entity representing a task within a goal.
Implements domain logic for task management and status tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid


class TaskStatus(Enum):
    """Task status enumeration"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """Task priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Task:
    """
    Task domain entity

    Represents a single task with business logic for status management,
    progress tracking, and scheduling.
    """

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: Optional[str] = None
    user_id: int = 0

    # Task details
    title: str = ""
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    due_date: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Progress tracking
    estimated_duration: Optional[int] = None  # in minutes
    actual_duration: Optional[int] = None  # in minutes
    progress_percentage: float = 0.0

    # Subtasks and dependencies
    subtasks: List["Task"] = field(default_factory=list)
    parent_task_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # Task IDs

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization validation and setup"""
        if not self.title.strip():
            raise ValueError("Task title cannot be empty")

        if self.user_id <= 0:
            raise ValueError("User ID must be positive")

        if self.progress_percentage < 0 or self.progress_percentage > 100:
            raise ValueError("Progress percentage must be between 0 and 100")

        # Update timestamp
        self.updated_at = datetime.now()

        # Auto-start in-progress tasks
        if self.status == TaskStatus.IN_PROGRESS and not self.started_at:
            self.started_at = datetime.now()

        # Set completion timestamp for completed tasks
        if self.status == TaskStatus.COMPLETED and not self.completed_at:
            self.completed_at = datetime.now()
            self.progress_percentage = 100.0

    @property
    def is_completed(self) -> bool:
        """Check if task is completed"""
        return self.status == TaskStatus.COMPLETED

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        return (
            self.due_date is not None
            and datetime.now() > self.due_date
            and self.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
        )

    @property
    def is_in_progress(self) -> bool:
        """Check if task is in progress"""
        return self.status == TaskStatus.IN_PROGRESS

    @property
    def is_blocked(self) -> bool:
        """Check if task is blocked"""
        return self.status == TaskStatus.BLOCKED

    def start_task(self) -> None:
        """Start working on task"""
        if self.status == TaskStatus.COMPLETED:
            raise ValueError("Cannot start completed task")

        if self.status == TaskStatus.CANCELLED:
            raise ValueError("Cannot start cancelled task")

        self.status = TaskStatus.IN_PROGRESS

        if not self.started_at:
            self.started_at = datetime.now()

        self.updated_at = datetime.now()

    def complete_task(self) -> None:
        """Mark task as completed"""
        if self.status == TaskStatus.CANCELLED:
            raise ValueError("Cannot complete cancelled task")

        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.progress_percentage = 100.0
        self.updated_at = datetime.now()

        # Calculate actual duration if task was started
        if self.started_at:
            duration_delta = self.completed_at - self.started_at
            self.actual_duration = int(duration_delta.total_seconds() / 60)

    def cancel_task(self) -> None:
        """Cancel task"""
        if self.status == TaskStatus.COMPLETED:
            raise ValueError("Cannot cancel completed task")

        self.status = TaskStatus.CANCELLED
        self.updated_at = datetime.now()

    def block_task(self, reason: Optional[str] = None) -> None:
        """Block task with optional reason"""
        if self.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            raise ValueError("Cannot block completed or cancelled task")

        self.status = TaskStatus.BLOCKED
        self.updated_at = datetime.now()

        if reason:
            self.metadata["blocked_reason"] = reason

    def unblock_task(self) -> None:
        """Unblock task and return to appropriate status"""
        if self.status != TaskStatus.BLOCKED:
            raise ValueError("Task is not blocked")

        # Return to in-progress if was started, otherwise todo
        self.status = TaskStatus.IN_PROGRESS if self.started_at else TaskStatus.TODO
        self.updated_at = datetime.now()

        # Remove blocked reason
        self.metadata.pop("blocked_reason", None)

    def update_progress(self, percentage: float) -> None:
        """
        Update task progress percentage

        Args:
            percentage: Progress percentage (0.0 to 100.0)
        """
        if percentage < 0 or percentage > 100:
            raise ValueError("Progress percentage must be between 0 and 100")

        self.progress_percentage = percentage
        self.updated_at = datetime.now()

        # Auto-complete if 100%
        if percentage == 100.0 and self.status != TaskStatus.COMPLETED:
            self.complete_task()

        # Auto-start if progress > 0 and not started
        elif percentage > 0 and self.status == TaskStatus.TODO:
            self.start_task()

    def add_subtask(self, subtask: "Task") -> None:
        """
        Add subtask to this task

        Args:
            subtask: Subtask to add
        """
        if not subtask.id:
            raise ValueError("Subtask must have valid ID")

        # Check for duplicate subtask IDs
        if any(st.id == subtask.id for st in self.subtasks):
            raise ValueError(f"Subtask with ID {subtask.id} already exists")

        # Set parent reference
        subtask.parent_task_id = self.id
        subtask.goal_id = self.goal_id
        subtask.user_id = self.user_id

        # Add to subtasks list
        self.subtasks.append(subtask)
        self.updated_at = datetime.now()

    def remove_subtask(self, subtask_id: str) -> bool:
        """
        Remove subtask from this task

        Args:
            subtask_id: ID of subtask to remove

        Returns:
            bool: True if subtask was removed, False if not found
        """
        original_count = len(self.subtasks)
        self.subtasks = [st for st in self.subtasks if st.id != subtask_id]

        if len(self.subtasks) < original_count:
            self.updated_at = datetime.now()
            return True

        return False

    def calculate_progress_from_subtasks(self) -> float:
        """
        Calculate progress based on subtask completion

        Returns:
            float: Progress percentage based on subtasks
        """
        if not self.subtasks:
            return self.progress_percentage

        total_progress = sum(st.progress_percentage for st in self.subtasks)
        return total_progress / len(self.subtasks)

    def get_completed_subtasks(self) -> List["Task"]:
        """Get list of completed subtasks"""
        return [st for st in self.subtasks if st.is_completed]

    def get_pending_subtasks(self) -> List["Task"]:
        """Get list of pending subtasks"""
        return [st for st in self.subtasks if not st.is_completed]

    def add_dependency(self, task_id: str) -> None:
        """Add task dependency"""
        if task_id == self.id:
            raise ValueError("Task cannot depend on itself")

        if task_id not in self.dependencies:
            self.dependencies.append(task_id)
            self.updated_at = datetime.now()

    def remove_dependency(self, task_id: str) -> bool:
        """Remove task dependency"""
        if task_id in self.dependencies:
            self.dependencies.remove(task_id)
            self.updated_at = datetime.now()
            return True
        return False

    def has_dependency(self, task_id: str) -> bool:
        """Check if task has specific dependency"""
        return task_id in self.dependencies

    def get_days_until_due(self) -> Optional[int]:
        """
        Get number of days until due date

        Returns:
            Optional[int]: Days until due, None if no due date
        """
        if not self.due_date:
            return None

        delta = self.due_date - datetime.now()
        return delta.days

    def get_duration_estimate_hours(self) -> Optional[float]:
        """Get estimated duration in hours"""
        if self.estimated_duration is None:
            return None
        return self.estimated_duration / 60.0

    def get_actual_duration_hours(self) -> Optional[float]:
        """Get actual duration in hours"""
        if self.actual_duration is None:
            return None
        return self.actual_duration / 60.0

    def get_time_spent(self) -> Optional[int]:
        """
        Get time spent on task in minutes

        Returns:
            Optional[int]: Minutes spent, None if not started
        """
        if not self.started_at:
            return None

        end_time = self.completed_at or datetime.now()
        delta = end_time - self.started_at
        return int(delta.total_seconds() / 60)

    def add_tag(self, tag: str) -> None:
        """Add tag to task"""
        tag = tag.strip().lower()
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()

    def remove_tag(self, tag: str) -> bool:
        """Remove tag from task"""
        tag = tag.strip().lower()
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
            return True
        return False

    def has_tag(self, tag: str) -> bool:
        """Check if task has specific tag"""
        return tag.strip().lower() in self.tags

    def set_due_date(self, due_date: datetime) -> None:
        """Set task due date"""
        if due_date <= datetime.now():
            raise ValueError("Due date cannot be in the past")

        self.due_date = due_date
        self.updated_at = datetime.now()

    def set_estimated_duration(self, minutes: int) -> None:
        """Set estimated duration in minutes"""
        if minutes <= 0:
            raise ValueError("Estimated duration must be positive")

        self.estimated_duration = minutes
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation"""
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
            "progress_percentage": self.progress_percentage,
            "parent_task_id": self.parent_task_id,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "metadata": self.metadata,
            "is_completed": self.is_completed,
            "is_overdue": self.is_overdue,
            "subtasks_count": len(self.subtasks),
            "completed_subtasks_count": len(self.get_completed_subtasks()),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create task from dictionary representation"""
        task = cls(
            id=data.get("id", str(uuid.uuid4())),
            goal_id=data.get("goal_id"),
            user_id=data.get("user_id", 0),
            title=data.get("title", ""),
            description=data.get("description"),
            status=TaskStatus(data.get("status", "todo")),
            priority=TaskPriority(data.get("priority", "medium")),
            estimated_duration=data.get("estimated_duration"),
            actual_duration=data.get("actual_duration"),
            progress_percentage=data.get("progress_percentage", 0.0),
            parent_task_id=data.get("parent_task_id"),
            dependencies=data.get("dependencies", []),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

        # Set timestamps if provided
        if "created_at" in data:
            task.created_at = datetime.fromisoformat(data["created_at"])

        if "updated_at" in data:
            task.updated_at = datetime.fromisoformat(data["updated_at"])

        if data.get("due_date"):
            task.due_date = datetime.fromisoformat(data["due_date"])

        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])

        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])

        return task

    def __repr__(self) -> str:
        """String representation of task"""
        return f"Task(id='{self.id}', title='{self.title}', status='{self.status.value}', progress={self.progress_percentage}%)"

    def __eq__(self, other) -> bool:
        """Equality comparison based on ID"""
        if not isinstance(other, Task):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID"""
        return hash(self.id)
