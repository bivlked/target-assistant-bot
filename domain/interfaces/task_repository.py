"""
Task Repository Interface

Defines the contract for task data persistence operations.
Implements Repository pattern for domain layer.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from domain.entities.task import Task, TaskStatus, TaskPriority


class TaskRepository(ABC):
    """
    Abstract repository interface for Task entity

    Defines all persistence operations for tasks following
    the Repository pattern principles.
    """

    @abstractmethod
    async def create(self, task: Task) -> Task:
        """
        Create a new task

        Args:
            task: Task entity to create

        Returns:
            Task: Created task with updated timestamps
        """
        pass

    @abstractmethod
    async def get_by_id(self, task_id: str) -> Optional[Task]:
        """
        Get task by ID

        Args:
            task_id: Unique task identifier

        Returns:
            Optional[Task]: Task if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_goal_id(self, goal_id: str) -> List[Task]:
        """
        Get all tasks for a goal

        Args:
            goal_id: Goal identifier

        Returns:
            List[Task]: List of goal's tasks
        """
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> List[Task]:
        """
        Get all tasks for a user

        Args:
            user_id: User identifier

        Returns:
            List[Task]: List of user's tasks
        """
        pass

    @abstractmethod
    async def get_by_status(self, user_id: int, status: TaskStatus) -> List[Task]:
        """
        Get tasks by status for a user

        Args:
            user_id: User identifier
            status: Task status filter

        Returns:
            List[Task]: List of tasks with specified status
        """
        pass

    @abstractmethod
    async def get_overdue(self, user_id: int) -> List[Task]:
        """
        Get overdue tasks for a user

        Args:
            user_id: User identifier

        Returns:
            List[Task]: List of overdue tasks
        """
        pass

    @abstractmethod
    async def get_due_today(self, user_id: int) -> List[Task]:
        """
        Get tasks due today for a user

        Args:
            user_id: User identifier

        Returns:
            List[Task]: List of tasks due today
        """
        pass

    @abstractmethod
    async def update(self, task: Task) -> Task:
        """
        Update existing task

        Args:
            task: Task entity with updates

        Returns:
            Task: Updated task
        """
        pass

    @abstractmethod
    async def delete(self, task_id: str) -> bool:
        """
        Delete task by ID

        Args:
            task_id: Task identifier

        Returns:
            bool: True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def search(self, user_id: int, query: str) -> List[Task]:
        """
        Search tasks by title/description

        Args:
            user_id: User identifier
            query: Search query string

        Returns:
            List[Task]: List of matching tasks
        """
        pass
