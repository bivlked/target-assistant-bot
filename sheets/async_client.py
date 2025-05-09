from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, List, Optional

from sheets.client import SheetsManager  # существующий синхронный клиент


class AsyncSheetsManager:
    """Асинхронная обёртка над SheetsManager, выполняющая вызовы в ThreadPoolExecutor.

    Это минимальная адаптация, позволяющая постепенно мигрировать код на async/await,
    не переписывая сразу всю логику работы с Google Sheets.
    """

    def __init__(
        self, max_workers: int = 4, loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        self._sync = SheetsManager()
        self._loop = loop or asyncio.get_event_loop()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    # ---------------------------- proxy helpers ---------------------------
    async def _run(self, func, *args, **kwargs):  # noqa: D401
        return await self._loop.run_in_executor(
            self._executor, lambda: func(*args, **kwargs)
        )

    # ----------------------------- Публичные API --------------------------
    async def create_spreadsheet(self, user_id: int):
        return await self._run(self._sync.create_spreadsheet, user_id)

    async def save_goal_info(self, user_id: int, goal_data: dict[str, str]) -> str:
        return await self._run(self._sync.save_goal_info, user_id, goal_data)

    async def save_plan(self, user_id: int, plan: List[dict[str, Any]]):
        await self._run(self._sync.save_plan, user_id, plan)

    async def get_statistics(self, user_id: int):
        return await self._run(self._sync.get_statistics, user_id)

    async def get_task_for_date(self, user_id: int, target_date: str):
        """Возвращает задачу на указанную дату (обёртка sync)."""
        return await self._run(self._sync.get_task_for_date, user_id, target_date)

    async def get_spreadsheet_url(self, user_id: int) -> str:
        return await self._run(self._sync.get_spreadsheet_url, user_id)

    def __getattr__(self, name):
        """Автоматически проксирует любой sync-метод как async-корутину.

        Это даёт полное покрытие API SheetsManager без ручного дублирования.
        """
        sync_attr = getattr(self._sync, name)
        if callable(sync_attr):

            async def _async_proxy(*args, **kwargs):  # type: ignore[override]
                return await self._run(sync_attr, *args, **kwargs)

            return _async_proxy
        return sync_attr

    # Позволяет корректно завершать пул потоков при необходимости
    async def aclose(self):  # noqa: D401
        self._executor.shutdown(wait=True)
