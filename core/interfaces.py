from __future__ import annotations

"""Common interfaces (Protocols) for dependency injection.
These allow GoalManager to depend on abstractions rather than concrete
Google-Sheets or OpenAI implementations.
"""

from typing import Protocol, Any, Dict, List, Optional, Tuple

from core.models import Goal, GoalPriority, GoalStatistics, GoalStatus, Task


class StorageInterface(Protocol):
    """Storage interface for goals and tasks with multi-goal support."""

    # Spreadsheet management
    def create_spreadsheet(self, user_id: int) -> None:
        """Create a new spreadsheet for user."""
        ...

    def delete_spreadsheet(self, user_id: int) -> None:
        """Delete user's spreadsheet."""
        ...

    # Goal management
    def get_all_goals(self, user_id: int) -> List[Goal]:
        """Get all goals for a user."""
        ...

    def get_goal_by_id(self, user_id: int, goal_id: int) -> Optional[Goal]:
        """Get a specific goal by ID."""
        ...

    def get_active_goals(self, user_id: int) -> List[Goal]:
        """Get only active goals."""
        ...

    def get_active_goals_count(self, user_id: int) -> int:
        """Count active goals."""
        ...

    def get_next_goal_id(self, user_id: int) -> int:
        """Get next available goal ID."""
        ...

    def save_goal_info(self, user_id: int, goal: Goal) -> str:
        """Save or update goal information."""
        ...

    def update_goal_status(
        self, user_id: int, goal_id: int, status: GoalStatus
    ) -> None:
        """Update goal status."""
        ...

    def update_goal_progress(self, user_id: int, goal_id: int, progress: int) -> None:
        """Update goal progress percentage."""
        ...

    def update_goal_priority(
        self, user_id: int, goal_id: int, priority: GoalPriority
    ) -> None:
        """Update goal priority."""
        ...

    def archive_goal(self, user_id: int, goal_id: int) -> None:
        """Archive a goal."""
        ...

    def delete_goal(self, user_id: int, goal_id: int) -> None:
        """Delete a goal completely."""
        ...

    # Plan management
    def save_plan(self, user_id: int, goal_id: int, plan: List[Dict[str, Any]]) -> None:
        """Save plan for a goal."""
        ...

    def get_plan_for_goal(self, user_id: int, goal_id: int) -> List[Task]:
        """Get plan for a specific goal."""
        ...

    # Task management
    def get_task_for_date(
        self, user_id: int, goal_id: int, date: str
    ) -> Optional[Task]:
        """Get task for specific goal and date."""
        ...

    def get_all_tasks_for_date(self, user_id: int, date: str) -> List[Task]:
        """Get all tasks for a specific date."""
        ...

    def update_task_status(
        self, user_id: int, goal_id: int, date: str, status: str
    ) -> None:
        """Update task status."""
        ...

    def batch_update_task_statuses(
        self, user_id: int, updates: Dict[Tuple[int, str], str]
    ) -> None:
        """Batch update multiple task statuses."""
        ...

    # Statistics
    def get_goal_statistics(self, user_id: int, goal_id: int) -> GoalStatistics:
        """Get statistics for a specific goal."""
        ...

    def get_overall_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get overall statistics for all goals."""
        ...

    # Legacy methods (to be deprecated)
    def get_goal_info(self, user_id: int) -> Dict[str, str]:
        """Get goal info (legacy, single goal)."""
        ...

    def save_goal_and_plan(
        self, user_id: int, goal_data: Dict[str, str], plan: List[Dict[str, Any]]
    ) -> str:
        """Save goal and plan (legacy, single goal)."""
        ...

    def get_status_message(self, user_id: int) -> str:
        """Get status message (legacy, single goal)."""
        ...


class AsyncStorageInterface(Protocol):
    """Async storage interface for goals and tasks with multi-goal support."""

    # Spreadsheet management
    async def create_spreadsheet(self, user_id: int) -> None:
        """Create a new spreadsheet for user."""
        ...

    async def delete_spreadsheet(self, user_id: int) -> None:
        """Delete user's spreadsheet."""
        ...

    # Goal management
    async def get_all_goals(self, user_id: int) -> List[Goal]:
        """Get all goals for a user."""
        ...

    async def get_goal_by_id(self, user_id: int, goal_id: int) -> Optional[Goal]:
        """Get a specific goal by ID."""
        ...

    async def get_active_goals(self, user_id: int) -> List[Goal]:
        """Get only active goals."""
        ...

    async def get_active_goals_count(self, user_id: int) -> int:
        """Count active goals."""
        ...

    async def get_next_goal_id(self, user_id: int) -> int:
        """Get next available goal ID."""
        ...

    async def save_goal_info(self, user_id: int, goal: Goal) -> str:
        """Save or update goal information."""
        ...

    async def update_goal_status(
        self, user_id: int, goal_id: int, status: GoalStatus
    ) -> None:
        """Update goal status."""
        ...

    async def update_goal_progress(
        self, user_id: int, goal_id: int, progress: int
    ) -> None:
        """Update goal progress percentage."""
        ...

    async def update_goal_priority(
        self, user_id: int, goal_id: int, priority: GoalPriority
    ) -> None:
        """Update goal priority."""
        ...

    async def archive_goal(self, user_id: int, goal_id: int) -> None:
        """Archive a goal."""
        ...

    async def delete_goal(self, user_id: int, goal_id: int) -> None:
        """Delete a goal completely."""
        ...

    # Plan management
    async def save_plan(
        self, user_id: int, goal_id: int, plan: List[Dict[str, Any]]
    ) -> None:
        """Save plan for a goal."""
        ...

    async def get_plan_for_goal(self, user_id: int, goal_id: int) -> List[Task]:
        """Get plan for a specific goal."""
        ...

    # Task management
    async def get_task_for_date(
        self, user_id: int, goal_id: int, date: str
    ) -> Optional[Task]:
        """Get task for specific goal and date."""
        ...

    async def get_all_tasks_for_date(self, user_id: int, date: str) -> List[Task]:
        """Get all tasks for a specific date."""
        ...

    async def update_task_status(
        self, user_id: int, goal_id: int, date: str, status: str
    ) -> None:
        """Update task status."""
        ...

    async def batch_update_task_statuses(
        self, user_id: int, updates: Dict[Tuple[int, str], str]
    ) -> None:
        """Batch update multiple task statuses."""
        ...

    # Statistics
    async def get_goal_statistics(self, user_id: int, goal_id: int) -> GoalStatistics:
        """Get statistics for a specific goal."""
        ...

    async def get_overall_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get overall statistics for all goals."""
        ...

    # Legacy methods (to be deprecated)
    async def get_goal_info(self, user_id: int) -> Dict[str, str]:
        """Get goal info (legacy, single goal)."""
        ...

    async def save_goal_and_plan(
        self, user_id: int, goal_data: Dict[str, str], plan: List[Dict[str, Any]]
    ) -> str:
        """Save goal and plan (legacy, single goal)."""
        ...

    async def get_status_message(self, user_id: int) -> str:
        """Get status message (legacy, single goal)."""
        ...

    async def get_task_for_today(self, user_id: int) -> Dict[str, Any] | None:
        """Get today's task (legacy, single goal)."""
        ...

    async def update_task_status_old(
        self, user_id: int, date: str, status: str
    ) -> None:
        """Update task status (legacy, single goal)."""
        ...

    async def get_extended_statistics(
        self, user_id: int, count: int = 7
    ) -> Dict[str, Any]:
        """Get extended statistics (legacy method)."""
        ...


class LLMInterface(Protocol):
    """Interface for LLM interactions."""

    def generate_plan(
        self, goal_text: str, deadline_str: str, available_time_str: str
    ) -> List[Dict[str, Any]]:
        """Generate a plan for achieving a goal."""
        ...

    def generate_motivation(self, goal_info: str, progress_summary: str) -> str:
        """Generate motivational message based on goal and progress."""
        ...


class AsyncLLMInterface(Protocol):
    """Async interface for LLM interactions."""

    async def generate_plan(
        self, goal_text: str, deadline_str: str, available_time_str: str
    ) -> List[Dict[str, Any]]:
        """Generate a plan for achieving a goal."""
        ...

    async def generate_motivation(self, goal_info: str, progress_summary: str) -> str:
        """Generate motivational message based on goal and progress."""
        ...
