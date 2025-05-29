from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from core.models import Goal, GoalPriority, GoalStatistics, GoalStatus, Task
from sheets.client import SheetsManager
from utils.cache import invalidate_sheet_cache


class AsyncSheetsManager:
    """Asynchronous wrapper around SheetsManager with multi-goal support.

    This class provides an asynchronous interface for all operations defined in
    `AsyncStorageInterface`. It achieves this by running the synchronous methods of
    `SheetsManager` in a `ThreadPoolExecutor`, thus making them non-blocking
    for an asyncio event loop.

    Implements the `AsyncStorageInterface` protocol.
    """

    def __init__(self, max_workers: int = 4):
        """Initializes the AsyncSheetsManager.

        Args:
            max_workers: The number of worker threads for the ThreadPoolExecutor
                         to run blocking Google API calls.
        """
        self._sync = SheetsManager()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    # ---------------------------- proxy helpers ---------------------------
    async def _run(self, func, *args, **kwargs):
        """Executes a synchronous function in the thread pool.

        Args:
            func: The synchronous function to execute.
            *args: Positional arguments for `func`.
            **kwargs: Keyword arguments for `func`.

        Returns:
            The result of `func(*args, **kwargs)`.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))

    # ----------------------------- Multi-goal API --------------------------
    async def get_all_goals(self, user_id: int) -> List[Goal]:
        """Get all goals for a user."""
        return await self._run(self._sync.get_all_goals, user_id)

    async def get_goal_by_id(self, user_id: int, goal_id: int) -> Optional[Goal]:
        """Get a specific goal by ID."""
        return await self._run(self._sync.get_goal_by_id, user_id, goal_id)

    async def get_active_goals(self, user_id: int) -> List[Goal]:
        """Get only active goals."""
        return await self._run(self._sync.get_active_goals, user_id)

    async def get_active_goals_count(self, user_id: int) -> int:
        """Count active goals."""
        return await self._run(self._sync.get_active_goals_count, user_id)

    async def get_next_goal_id(self, user_id: int) -> int:
        """Get next available goal ID."""
        return await self._run(self._sync.get_next_goal_id, user_id)

    async def save_goal_info(self, user_id: int, goal: Goal) -> str:
        """Save or update goal information."""
        try:
            return await self._run(self._sync.save_goal_info, user_id, goal)
        finally:
            invalidate_sheet_cache(user_id)

    async def update_goal_status(
        self, user_id: int, goal_id: int, status: GoalStatus
    ) -> None:
        """Update goal status."""
        try:
            return await self._run(
                self._sync.update_goal_status, user_id, goal_id, status
            )
        finally:
            invalidate_sheet_cache(user_id)

    async def update_goal_progress(
        self, user_id: int, goal_id: int, progress: int
    ) -> None:
        """Update goal progress percentage."""
        try:
            return await self._run(
                self._sync.update_goal_progress, user_id, goal_id, progress
            )
        finally:
            invalidate_sheet_cache(user_id)

    async def update_goal_priority(
        self, user_id: int, goal_id: int, priority: GoalPriority
    ) -> None:
        """Update goal priority."""
        try:
            return await self._run(
                self._sync.update_goal_priority, user_id, goal_id, priority
            )
        finally:
            invalidate_sheet_cache(user_id)

    async def archive_goal(self, user_id: int, goal_id: int) -> None:
        """Archive a goal."""
        try:
            return await self._run(self._sync.archive_goal, user_id, goal_id)
        finally:
            invalidate_sheet_cache(user_id)

    async def delete_goal(self, user_id: int, goal_id: int) -> None:
        """Delete a goal completely."""
        try:
            return await self._run(self._sync.delete_goal, user_id, goal_id)
        finally:
            invalidate_sheet_cache(user_id)

    async def save_plan(
        self, user_id: int, goal_id: int, plan: List[Dict[str, Any]]
    ) -> None:
        """Save plan for a goal."""
        try:
            return await self._run(self._sync.save_plan, user_id, goal_id, plan)
        finally:
            invalidate_sheet_cache(user_id)

    async def get_plan_for_goal(self, user_id: int, goal_id: int) -> List[Task]:
        """Get plan for a specific goal."""
        return await self._run(self._sync.get_plan_for_goal, user_id, goal_id)

    async def get_task_for_date(
        self, user_id: int, goal_id: int, date: str
    ) -> Optional[Task]:
        """Get task for specific goal and date."""
        return await self._run(self._sync.get_task_for_date, user_id, goal_id, date)

    async def get_all_tasks_for_date(self, user_id: int, date: str) -> List[Task]:
        """Get all tasks for a specific date."""
        return await self._run(self._sync.get_all_tasks_for_date, user_id, date)

    async def update_task_status(
        self, user_id: int, goal_id: int, date: str, status: str
    ) -> None:
        """Update task status."""
        try:
            return await self._run(
                self._sync.update_task_status, user_id, goal_id, date, status
            )
        finally:
            invalidate_sheet_cache(user_id)

    async def batch_update_task_statuses(
        self, user_id: int, updates: Dict[Tuple[int, str], str]
    ) -> None:
        """Batch update multiple task statuses."""
        try:
            return await self._run(
                self._sync.batch_update_task_statuses, user_id, updates
            )
        finally:
            invalidate_sheet_cache(user_id)

    async def get_goal_statistics(self, user_id: int, goal_id: int) -> GoalStatistics:
        """Get statistics for a specific goal."""
        return await self._run(self._sync.get_goal_statistics, user_id, goal_id)

    async def get_overall_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get overall statistics for all goals."""
        return await self._run(self._sync.get_overall_statistics, user_id)

    # ----------------------------- Legacy API --------------------------
    async def create_spreadsheet(self, user_id: int):
        """Creates (if not exists) or opens a user's spreadsheet."""
        return await self._run(self._sync.create_spreadsheet, user_id)

    async def clear_user_data(self, user_id: int):
        """Clears all data - legacy method that now archives all goals."""
        try:
            return await self._run(self._sync.clear_user_data, user_id)
        finally:
            invalidate_sheet_cache(user_id)

    async def get_goal_info(self, user_id: int) -> Dict[str, str]:
        """Legacy method - returns info for first active goal."""
        return await self._run(self._sync.get_goal_info, user_id)

    async def save_goal_and_plan(
        self, user_id: int, goal_data: Dict[str, str], plan: List[Dict[str, Any]]
    ) -> str:
        """Legacy method - creates goal as ID 1."""
        try:
            return await self._run(
                self._sync.save_goal_and_plan, user_id, goal_data, plan
            )
        finally:
            invalidate_sheet_cache(user_id)

    async def get_task_for_today(self, user_id: int) -> Dict[str, Any] | None:
        """Legacy method - returns first task for today."""
        return await self._run(self._sync.get_task_for_today, user_id)

    async def update_task_status_old(
        self, user_id: int, date: str, status: str
    ) -> None:
        """Legacy method - updates status for first goal's task."""
        try:
            return await self._run(
                self._sync.update_task_status_old, user_id, date, status
            )
        finally:
            invalidate_sheet_cache(user_id)

    async def get_status_message(self, user_id: int) -> str:
        """Legacy method - returns status for first goal."""
        return await self._run(self._sync.get_status_message, user_id)

    async def delete_spreadsheet(self, user_id: int):
        """Permanently deletes the user's spreadsheet from Google Drive."""
        try:
            return await self._run(self._sync.delete_spreadsheet, user_id)
        finally:
            invalidate_sheet_cache(user_id)

    async def get_spreadsheet_url(self, user_id: int) -> str:
        """Returns the URL of the user's spreadsheet."""
        return await self._run(self._sync.get_spreadsheet_url, user_id)

    async def get_extended_statistics(
        self, user_id: int, upcoming_count: int = 5
    ) -> Dict[str, Any]:
        """Legacy extended statistics - uses first active goal."""
        return await self._run(
            self._sync.get_extended_statistics, user_id, upcoming_count
        )

    # Legacy aliases for compatibility
    async def get_statistics(self, user_id: int) -> str:
        """Alias for get_status_message."""
        return await self.get_status_message(user_id)

    async def get_task_for_date_legacy(
        self, user_id: int, date: str
    ) -> Dict[str, Any] | None:
        """Legacy version - gets task from first active goal."""
        goals = await self.get_active_goals(user_id)
        if goals:
            task = await self.get_task_for_date(user_id, goals[0].goal_id, date)
            if task:
                return {
                    "Дата": task.date,
                    "День недели": task.day_of_week,
                    "Задача": task.task,
                    "Статус": task.status.value,
                }
        return None

    # ----------------------------- Cleanup --------------------------
    async def aclose(self):
        """Shuts down the internal ThreadPoolExecutor."""
        self._executor.shutdown(wait=True)

    def __getattr__(self, name):
        """Generic attribute proxy for other `SheetsManager` methods.

        Allows any method of the synchronous `_sync` instance (SheetsManager)
        to be called asynchronously on this `AsyncSheetsManager` instance.
        """
        sync_attr = getattr(self._sync, name)
        if callable(sync_attr):

            async def _async_proxy(*args, **kwargs):
                return await self._run(sync_attr, *args, **kwargs)

            return _async_proxy
        return sync_attr
