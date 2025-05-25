from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, List, Optional, Dict

from sheets.client import SheetsManager  # существующий синхронный клиент
from utils.cache import invalidate_sheet_cache


class AsyncSheetsManager:
    """Asynchronous wrapper around :class:`sheets.client.SheetsManager`.

    This class provides an asynchronous interface for all operations defined in
    `StorageInterface`. It achieves this by running the synchronous methods of
    `SheetsManager` in a `ThreadPoolExecutor`, thus making them non-blocking
    for an asyncio event loop.

    This allows for gradual migration to async/await without rewriting the core
    synchronous Google Sheets interaction logic immediately.

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
    async def _run(self, func, *args, **kwargs):  # noqa: D401
        """Executes a synchronous function `func` in the thread pool.

        Args:
            func: The synchronous function to execute.
            *args: Positional arguments for `func`.
            **kwargs: Keyword arguments for `func`.

        Returns:
            The result of `func(*args, **kwargs)`.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))

    # ----------------------------- Публичные API --------------------------
    async def create_spreadsheet(self, user_id: int):
        """Async version of `SheetsManager.create_spreadsheet`."""
        return await self._run(self._sync.create_spreadsheet, user_id)

    async def save_goal_info(self, user_id: int, goal_data: dict[str, str]) -> str:
        """Async version of `SheetsManager.save_goal_info`."""
        try:
            return await self._run(self._sync.save_goal_info, user_id, goal_data)
        finally:
            invalidate_sheet_cache(user_id)

    async def save_plan(self, user_id: int, plan: List[dict[str, Any]]):
        """Async version of `SheetsManager.save_plan`."""
        try:
            return await self._run(self._sync.save_plan, user_id, plan)
        finally:
            invalidate_sheet_cache(user_id)

    async def get_statistics(self, user_id: int):
        """Async version of `SheetsManager.get_statistics`."""
        return await self._run(self._sync.get_statistics, user_id)

    async def get_task_for_date(self, user_id: int, target_date: str):
        """Async version of `SheetsManager.get_task_for_date`."""
        return await self._run(self._sync.get_task_for_date, user_id, target_date)

    async def get_spreadsheet_url(self, user_id: int) -> str:
        """Async version of `SheetsManager.get_spreadsheet_url`."""
        return await self._run(self._sync.get_spreadsheet_url, user_id)

    def __getattr__(self, name):
        """Generic attribute proxy for other `SheetsManager` methods.

        Allows any method of the synchronous `_sync` instance (SheetsManager)
        to be called asynchronously on this `AsyncSheetsManager` instance.
        For example, `await async_manager.some_other_method()` would run
        `self._sync.some_other_method()` in the thread pool.

        Warning: This provides broad proxying. For methods that are part of the
        `AsyncStorageInterface`, explicit `async def` wrappers are preferred for clarity
        and to handle specific logic like cache invalidation.
        """
        sync_attr = getattr(self._sync, name)
        if callable(sync_attr):

            async def _async_proxy(*args, **kwargs):  # type: ignore[override]
                return await self._run(sync_attr, *args, **kwargs)

            return _async_proxy
        return sync_attr

    # Позволяет корректно завершать пул потоков при необходимости
    async def aclose(self):  # noqa: D401
        """Shuts down the internal ThreadPoolExecutor."""
        self._executor.shutdown(wait=True)

    async def clear_user_data(self, user_id: int):
        """Async version of `SheetsManager.clear_user_data`."""
        try:
            return await self._run(self._sync.clear_user_data, user_id)
        finally:
            invalidate_sheet_cache(user_id)

    async def get_goal_info(self, user_id: int):
        """Async version of `SheetsManager.get_goal_info`."""
        return await self._run(self._sync.get_goal_info, user_id)

    async def update_task_status(self, user_id: int, target_date: str, status: str):
        """Async version of `SheetsManager.update_task_status`."""
        try:
            return await self._run(
                self._sync.update_task_status, user_id, target_date, status
            )
        finally:
            invalidate_sheet_cache(user_id)

    async def get_extended_statistics(self, user_id: int, upcoming_count: int = 5):
        """Async version of `SheetsManager.get_extended_statistics`."""
        return await self._run(
            self._sync.get_extended_statistics, user_id, upcoming_count
        )

    async def delete_spreadsheet(self, user_id: int):
        """Async version of `SheetsManager.delete_spreadsheet`."""
        try:
            return await self._run(self._sync.delete_spreadsheet, user_id)
        finally:
            invalidate_sheet_cache(user_id)

    async def batch_update_task_statuses(self, user_id: int, updates: dict[str, str]):
        """Async version of `SheetsManager.batch_update_task_statuses`."""
        try:
            return await self._run(
                self._sync.batch_update_task_statuses, user_id, updates
            )
        finally:
            invalidate_sheet_cache(user_id)
