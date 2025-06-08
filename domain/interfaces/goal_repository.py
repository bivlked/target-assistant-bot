"""
Goal Repository Interface

Defines the contract for goal data persistence operations.
Implements Repository pattern for domain layer.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from domain.entities.goal import Goal, GoalStatus, GoalPriority


class GoalRepository(ABC):
    """
    Abstract repository interface for Goal entity

    Defines all persistence operations for goals following
    the Repository pattern principles.
    """

    @abstractmethod
    async def create(self, goal: Goal) -> Goal:
        """
        Create a new goal

        Args:
            goal: Goal entity to create

        Returns:
            Goal: Created goal with updated timestamps

        Raises:
            RepositoryError: If creation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, goal_id: str) -> Optional[Goal]:
        """
        Get goal by ID

        Args:
            goal_id: Unique goal identifier

        Returns:
            Optional[Goal]: Goal if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> List[Goal]:
        """
        Get all goals for a user

        Args:
            user_id: User identifier

        Returns:
            List[Goal]: List of user's goals
        """
        pass

    @abstractmethod
    async def get_by_status(self, user_id: int, status: GoalStatus) -> List[Goal]:
        """
        Get goals by status for a user

        Args:
            user_id: User identifier
            status: Goal status filter

        Returns:
            List[Goal]: List of goals with specified status
        """
        pass

    @abstractmethod
    async def get_by_priority(self, user_id: int, priority: GoalPriority) -> List[Goal]:
        """
        Get goals by priority for a user

        Args:
            user_id: User identifier
            priority: Goal priority filter

        Returns:
            List[Goal]: List of goals with specified priority
        """
        pass

    @abstractmethod
    async def get_overdue(self, user_id: int) -> List[Goal]:
        """
        Get overdue goals for a user

        Args:
            user_id: User identifier

        Returns:
            List[Goal]: List of overdue goals
        """
        pass

    @abstractmethod
    async def get_by_tag(self, user_id: int, tag: str) -> List[Goal]:
        """
        Get goals by tag for a user

        Args:
            user_id: User identifier
            tag: Tag to filter by

        Returns:
            List[Goal]: List of goals with specified tag
        """
        pass

    @abstractmethod
    async def search(
        self,
        user_id: int,
        query: str,
        status: Optional[GoalStatus] = None,
        priority: Optional[GoalPriority] = None,
    ) -> List[Goal]:
        """
        Search goals by title/description

        Args:
            user_id: User identifier
            query: Search query string
            status: Optional status filter
            priority: Optional priority filter

        Returns:
            List[Goal]: List of matching goals
        """
        pass

    @abstractmethod
    async def update(self, goal: Goal) -> Goal:
        """
        Update existing goal

        Args:
            goal: Goal entity with updates

        Returns:
            Goal: Updated goal

        Raises:
            RepositoryError: If update fails or goal not found
        """
        pass

    @abstractmethod
    async def delete(self, goal_id: str) -> bool:
        """
        Delete goal by ID

        Args:
            goal_id: Goal identifier

        Returns:
            bool: True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def get_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get goal statistics for a user

        Args:
            user_id: User identifier

        Returns:
            Dict[str, Any]: Statistics including:
                - total_goals
                - completed_goals
                - active_goals
                - overdue_goals
                - completion_rate
        """
        pass

    @abstractmethod
    async def get_recent(self, user_id: int, limit: int = 10) -> List[Goal]:
        """
        Get recently updated goals for a user

        Args:
            user_id: User identifier
            limit: Maximum number of goals to return

        Returns:
            List[Goal]: List of recently updated goals
        """
        pass

    @abstractmethod
    async def get_due_soon(self, user_id: int, days_ahead: int = 7) -> List[Goal]:
        """
        Get goals due within specified days

        Args:
            user_id: User identifier
            days_ahead: Number of days to look ahead

        Returns:
            List[Goal]: List of goals due soon
        """
        pass

    @abstractmethod
    async def bulk_update_status(self, goal_ids: List[str], status: GoalStatus) -> int:
        """
        Update status for multiple goals

        Args:
            goal_ids: List of goal identifiers
            status: New status to set

        Returns:
            int: Number of goals updated
        """
        pass

    @abstractmethod
    async def get_completion_trends(
        self, user_id: int, days: int = 30
    ) -> Dict[str, Any]:
        """
        Get goal completion trends over time

        Args:
            user_id: User identifier
            days: Number of days to analyze

        Returns:
            Dict[str, Any]: Trend data including completion rates over time
        """
        pass
