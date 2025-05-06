from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from utils.helpers import format_date, get_day_of_week
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS

if TYPE_CHECKING:  # избегаем циклов импорта
    from sheets.client import SheetsManager
    from sheets.async_client import AsyncSheetsManager
    from llm.client import LLMClient
    from llm.async_client import AsyncLLMClient

# Типы строк статуса
STATUS_NOT_DONE = "Не выполнено"
STATUS_DONE = "Выполнено"
STATUS_PARTIAL = "Частично выполнено"

logger = logging.getLogger(__name__)


class GoalManager:
    """Бизнес-логика бота с поддержкой синхронных и асинхронных клиентов."""

    def __init__(
        self,
        sheets_sync: "SheetsManager | None" = None,
        llm_sync: "LLMClient | None" = None,
        sheets_async: "AsyncSheetsManager | None" = None,
        llm_async: "AsyncLLMClient | None" = None,
    ):
        if not (sheets_sync or sheets_async):
            raise ValueError("Нужен хотя бы один Sheets-клиент (sync/async)")
        if not (llm_sync or llm_async):
            raise ValueError("Нужен хотя бы один LLM-клиент (sync/async)")

        self.sheets_sync = sheets_sync
        self.sheets_async = sheets_async
        self.llm_sync = llm_sync
        self.llm_async = llm_async

        # для обратной совместимости со старым кодом
        self.sheets = sheets_sync or sheets_async  # type: ignore[assignment]
        self.llm = llm_sync or llm_async  # type: ignore[assignment]

    # ------------------------ sync API (остаётся для совместимости) ---------
    def setup_user(self, user_id: int) -> None:
        self.sheets.create_spreadsheet(user_id)

    # ... остальные sync-методы опущены, они вызывают sheets_sync/llm_sync напрямую ...

    # -----------------------------------------------------------------------
    # Async API (используется всерьёз)
    # -----------------------------------------------------------------------
    async def setup_user_async(self, user_id: int):
        import asyncio
        if self.sheets_async:
            await self.sheets_async.create_spreadsheet(user_id)  # type: ignore[attr-defined]
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.sheets_sync.create_spreadsheet, user_id)  # type: ignore[arg-type]

    async def reset_user_async(self, user_id: int):
        import asyncio
        if self.sheets_async:
            await self.sheets_async.delete_spreadsheet(user_id)  # type: ignore[attr-defined]
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.sheets_sync.delete_spreadsheet, user_id)  # type: ignore[arg-type]

    async def get_today_task_async(self, user_id: int):
        import asyncio
        date_str = format_date(datetime.now())
        if self.sheets_async:
            return await self.sheets_async.get_task_for_date(user_id, date_str)  # type: ignore[attr-defined]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.sheets_sync.get_task_for_date, user_id, date_str)  # type: ignore[arg-type]

    async def update_today_task_status_async(self, user_id: int, status: str):
        import asyncio
        date_str = format_date(datetime.now())
        if self.sheets_async:
            await self.sheets_async.update_task_status(user_id, date_str, status)  # type: ignore[attr-defined]
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.sheets_sync.update_task_status, user_id, date_str, status)  # type: ignore[arg-type]

    async def get_detailed_status_async(self, user_id: int):
        import asyncio
        if self.sheets_async:
            stats = await self.sheets_async.get_extended_statistics(user_id)  # type: ignore[attr-defined]
            goal_info = await self.sheets_async.get_goal_info(user_id)  # type: ignore[attr-defined]
        else:
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(None, self.sheets_sync.get_extended_statistics, user_id)  # type: ignore[arg-type]
            goal_info = await loop.run_in_executor(None, self.sheets_sync.get_goal_info, user_id)  # type: ignore[arg-type]
        return {"goal": goal_info.get("Глобальная цель", "—"), **stats}

    async def batch_update_task_statuses_async(self, user_id: int, updates: dict[str, str]):
        import asyncio
        if self.sheets_async:
            await self.sheets_async.batch_update_task_statuses(user_id, updates)  # type: ignore[attr-defined]
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.sheets_sync.batch_update_task_statuses, user_id, updates)  # type: ignore[arg-type]

    async def generate_motivation_message_async(self, user_id: int):
        import asyncio
        if self.sheets_async:
            goal_info = await self.sheets_async.get_goal_info(user_id)  # type: ignore[attr-defined]
            stats = await self.sheets_async.get_statistics(user_id)  # type: ignore[attr-defined]
        else:
            loop = asyncio.get_event_loop()
            goal_info = await loop.run_in_executor(None, self.sheets_sync.get_goal_info, user_id)  # type: ignore[arg-type]
            stats = await loop.run_in_executor(None, self.sheets_sync.get_statistics, user_id)  # type: ignore[arg-type]

        if self.llm_async:
            return await self.llm_async.generate_motivation(goal_info.get("Глобальная цель", ""), stats)  # type: ignore[attr-defined]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.llm_sync.generate_motivation, goal_info.get("Глобальная цель", ""), stats)  # type: ignore[arg-type]
