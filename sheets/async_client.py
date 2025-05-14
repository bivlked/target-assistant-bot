from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, List, Optional, Dict

from sheets.client import SheetsManager  # существующий синхронный клиент
from utils.cache import invalidate_sheet_cache


class AsyncSheetsManager:
    """Асинхронная обёртка над :class:`sheets.client.SheetsManager`.

    Все публичные методы синхронного клиента автоматически проксируются в
    корутины, которые выполняются в пуле потоков ``ThreadPoolExecutor``. Это
    обеспечивает *неблокирующее* взаимодействие с Google API и позволяет
    постепенно мигрировать кодовой базу в сторону **async/await** без
    переписывания всей бизнес-логики сразу.
    """

    def __init__(
        self, max_workers: int = 4, loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        """Создаёт обёртку.

        Параметры
        ----------
        max_workers: int
            Количество потоков, в которых будут выполняться блокирующие
            обращения к Google API.
        loop: asyncio.AbstractEventLoop | None
            Event-loop, в контексте которого запускаются корутины.
            Если *None*, используется «текущий» loop, возвращаемый
            :pyfunc:`asyncio.get_event_loop`.
        """
        self._sync = SheetsManager()
        self._loop = loop or asyncio.get_event_loop()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    # ---------------------------- proxy helpers ---------------------------
    async def _run(self, func, *args, **kwargs):  # noqa: D401
        """Выполняет блокирующую функцию *func* в пуле потоков."""
        return await self._loop.run_in_executor(
            self._executor, lambda: func(*args, **kwargs)
        )

    # ----------------------------- Публичные API --------------------------
    async def create_spreadsheet(self, user_id: int):
        return await self._run(self._sync.create_spreadsheet, user_id)

    async def save_goal_info(self, user_id: int, goal_data: dict[str, str]) -> str:
        try:
            return await self._run(self._sync.save_goal_info, user_id, goal_data)
        finally:
            invalidate_sheet_cache(user_id)

    async def save_plan(self, user_id: int, plan: List[dict[str, Any]]):
        try:
            return await self._run(self._sync.save_plan, user_id, plan)
        finally:
            invalidate_sheet_cache(user_id)

    async def get_statistics(self, user_id: int):
        return await self._run(self._sync.get_statistics, user_id)

    async def get_task_for_date(self, user_id: int, target_date: str):
        """Возвращает задачу на указанную дату (обёртка sync)."""
        return await self._run(self._sync.get_task_for_date, user_id, target_date)

    async def get_spreadsheet_url(self, user_id: int) -> str:
        return await self._run(self._sync.get_spreadsheet_url, user_id)

    def __getattr__(self, name):
        """Магия для проксирования: любой вызов вида ``await client.foo()``
        будет прозрачно перенаправлен на ``SheetsManager.foo`` внутри
        ThreadPoolExecutor.
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

    async def clear_user_data(self, user_id: int):
        """Async: Очищает оба листа пользователя."""
        try:
            return await self._run(self._sync.clear_user_data, user_id)
        finally:
            invalidate_sheet_cache(user_id)

    async def get_goal_info(self, user_id: int):
        return await self._run(self._sync.get_goal_info, user_id)

    async def update_task_status(self, user_id: int, target_date: str, status: str):
        """Async: Обновляет поле *Статус* задачи."""
        try:
            return await self._run(
                self._sync.update_task_status, user_id, target_date, status
            )
        finally:
            invalidate_sheet_cache(user_id)

    async def get_extended_statistics(self, user_id: int, upcoming_count: int = 5):
        return await self._run(
            self._sync.get_extended_statistics, user_id, upcoming_count
        )

    async def delete_spreadsheet(self, user_id: int):
        """Async: Навсегда удаляет таблицу пользователя."""
        try:
            return await self._run(self._sync.delete_spreadsheet, user_id)
        finally:
            invalidate_sheet_cache(user_id)

    async def batch_update_task_statuses(self, user_id: int, updates: dict[str, str]):
        """Async: Пакетно обновляет статусы задач."""
        try:
            return await self._run(
                self._sync.batch_update_task_statuses, user_id, updates
            )
        finally:
            invalidate_sheet_cache(user_id)
