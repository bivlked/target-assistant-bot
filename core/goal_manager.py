from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional, Final, cast

from utils.helpers import format_date, get_day_of_week
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS

from core.interfaces import (
    StorageInterface,
    LLMInterface,
    AsyncStorageInterface,
    AsyncLLMInterface,
)
from utils.ratelimiter import UserRateLimiter, RateLimitException
from config import ratelimiter_cfg
from core.metrics import (
    LLM_API_CALLS,
    GOALS_SET_TOTAL,
    TASKS_STATUS_UPDATED_TOTAL,
)  # Import metrics

if TYPE_CHECKING:  # избегаем циклов импорта
    from sheets.client import SheetsManager
    from sheets.async_client import AsyncSheetsManager
    from llm.client import LLMClient
    from llm.async_client import AsyncLLMClient

# Типы строк статуса
STATUS_NOT_DONE: Final[str] = "Не выполнено"
STATUS_DONE: Final[str] = "Выполнено"
STATUS_PARTIAL: Final[str] = "Частично выполнено"

logger = logging.getLogger(__name__)


class GoalManager:
    """Manages the business logic for user goals, tasks, and interactions.

    This class orchestrates operations between Telegram handlers, data storage (Google Sheets),
    and the LLM for plan generation and motivation. It supports both synchronous and
    asynchronous operations by accepting respective client implementations.
    """

    def __init__(
        self,
        # Keep old names for backward compatibility with tests primarily
        sheets_sync: Optional[StorageInterface] = None,
        llm_sync: Optional[LLMInterface] = None,
        sheets_async: Optional[AsyncStorageInterface] = None,
        llm_async: Optional[AsyncLLMInterface] = None,
        # New DI-friendly names, to be preferred if provided
        storage_sync: Optional[StorageInterface] = None,
        storage_async: Optional[AsyncStorageInterface] = None,
    ):
        """Initializes the GoalManager with necessary dependencies.

        Args:
            sheets_sync: Synchronous storage client (e.g., SheetsManager).
            llm_sync: Synchronous LLM client.
            sheets_async: Asynchronous storage client (e.g., AsyncSheetsManager).
            llm_async: Asynchronous LLM client.
            storage_sync: Alternative DI-friendly name for sheets_sync.
            storage_async: Alternative DI-friendly name for sheets_async.

        Raises:
            ValueError: If neither synchronous nor asynchronous storage/LLM clients are provided.
        """
        # Определяем актуальных провайдеров, отдавая предпочтение новым именам
        actual_sheets_sync = storage_sync if storage_sync is not None else sheets_sync
        actual_llm_sync = llm_sync  # No alternative name for llm_sync yet
        actual_sheets_async = (
            storage_async if storage_async is not None else sheets_async
        )
        actual_llm_async = llm_async

        if not (actual_sheets_sync or actual_sheets_async):
            raise ValueError(
                "Either (storage_sync or sheets_sync) or (storage_async or sheets_async) must be provided"
            )
        if not (actual_llm_sync or actual_llm_async):
            raise ValueError("Either llm_sync or llm_async must be provided")

        # keep raw refs
        self.sheets_sync = actual_sheets_sync
        self.llm_sync = actual_llm_sync
        self.sheets_async = actual_sheets_async
        self.llm_async = actual_llm_async

        # Initialize rate limiter for LLM calls
        self.llm_rate_limiter = UserRateLimiter(
            default_tokens_per_second=ratelimiter_cfg.llm_requests_per_minute / 60,
            default_max_tokens=ratelimiter_cfg.llm_max_burst,
        )

        # These attributes are used both in sync and async context; exact concrete type
        # is not important at runtime, поэтому указываем Any, чтобы избежать NameError
        # из-за отсутствия реального класса, когда импорт находится под TYPE_CHECKING.
        self.sheets: Any = self.sheets_sync or self.sheets_async
        self.llm: Any = self.llm_sync or self.llm_async

    # -------------------------------------------------
    # Методы API, вызываемые из Telegram-обработчиков
    # -------------------------------------------------
    def setup_user(self, user_id: int) -> None:
        """Sets up the user by creating or opening their Google Spreadsheet.

        Called by the /start handler for initial infrastructure setup.
        If a spreadsheet for the user already exists, it will be opened.
        This method proxies the call to the appropriate storage client.

        Args:
            user_id: The Telegram ID of the user, used to generate a unique
                     spreadsheet name (e.g., TargetAssistant_<user_id>).
        """
        self.sheets.create_spreadsheet(user_id)

    def set_new_goal(
        self,
        user_id: int,
        goal_text: str,
        deadline_str: str,
        available_time_str: str,
    ) -> str:
        """Creates a new goal for the user, generates a plan, and saves it.

        This involves:
        1. Clearing any previous user data from the spreadsheet.
        2. Generating a new task plan using the LLM.
        3. Calculating dates for each task.
        4. Saving goal information and the full plan to the spreadsheet.

        Args:
            user_id: The user's Telegram ID.
            goal_text: The description of the goal.
            deadline_str: The deadline for the goal (e.g., "in 2 months").
            available_time_str: The time available daily (e.g., "1 hour").

        Returns:
            The URL of the Google Spreadsheet containing the goal and plan.
        """
        # 1. Очищаем предыдущие листы
        self.sheets.clear_user_data(user_id)

        # 1.5 Check rate limit for LLM
        try:
            self.llm_rate_limiter.check_limit(user_id)
        except RateLimitException as e:
            logger.warning(f"User {user_id} rate limited on generate_plan: {e}")
            LLM_API_CALLS.labels(
                method_name="generate_plan", status="ratelimited"
            ).inc()
            raise

        # 2. Генерируем план через LLM
        plan_json = self.llm.generate_plan(goal_text, deadline_str, available_time_str)

        # 3. Расчёт дат
        today = datetime.now()
        full_plan = []
        for item in plan_json:
            day_offset = item["day"] - 1
            date = today + timedelta(days=day_offset)
            full_plan.append(
                {
                    COL_DATE: format_date(date),
                    COL_DAYOFWEEK: get_day_of_week(date),
                    COL_TASK: item["task"],
                    COL_STATUS: STATUS_NOT_DONE,
                }
            )

        # 4. Сохраняем в Sheets
        goal_info = {
            "Глобальная цель": goal_text,
            "Срок выполнения": deadline_str,
            "Затраты в день": available_time_str,
            "Начало выполнения": format_date(today),
        }
        spreadsheet_url = self.sheets.save_goal_info(user_id, goal_info)
        self.sheets.save_plan(user_id, full_plan)

        GOALS_SET_TOTAL.inc()  # Increment goals set counter
        return spreadsheet_url

    def get_today_task(self, user_id: int):
        """Retrieves the task scheduled for the current day for the user.

        Args:
            user_id: The user's Telegram ID.

        Returns:
            A dictionary representing the task if found, otherwise None.
        """
        date_str = format_date(datetime.now())
        return self.sheets.get_task_for_date(user_id, date_str)

    def update_today_task_status(self, user_id: int, status: str):
        """Updates the status of today's task for the user.

        Args:
            user_id: The user's Telegram ID.
            status: The new status string (e.g., STATUS_DONE, STATUS_NOT_DONE).
        """
        date_str = format_date(datetime.now())
        self.sheets.update_task_status(user_id, date_str, status)
        TASKS_STATUS_UPDATED_TOTAL.labels(new_status=status).inc()

    def get_goal_status_details(self, user_id: int):
        """Gets a brief string summary of the user's goal progress.

        Note: This is an older method for basic status.
              Prefer `get_detailed_status` for more comprehensive information.

        Args:
            user_id: The user's Telegram ID.

        Returns:
            A string summarizing the goal statistics.
        """
        # Старая строковая статистика (для совместимости)
        return self.sheets.get_statistics(user_id)

    def generate_motivation_message(self, user_id: int):
        """Generates a motivational message for the user via LLM.

        Checks rate limits before calling the LLM.

        Args:
            user_id: The user's Telegram ID.

        Returns:
            A motivational message string.

        Raises:
            RateLimitException: If the user has exceeded their LLM call limit.
        """
        try:
            self.llm_rate_limiter.check_limit(user_id)
        except RateLimitException as e:
            logger.warning(f"User {user_id} rate limited on generate_motivation: {e}")
            LLM_API_CALLS.labels(
                method_name="generate_motivation", status="ratelimited"
            ).inc()
            raise

        goal_info = self.sheets.get_goal_info(user_id)
        stats = self.sheets.get_statistics(user_id)
        return self.llm.generate_motivation(goal_info.get("Глобальная цель", ""), stats)

    # -------------------------------------------------
    # Сброс
    # -------------------------------------------------
    def reset_user(self, user_id: int):
        """Completely deletes the user's Google Spreadsheet and associated data.

        Args:
            user_id: The user's Telegram ID.
        """
        self.sheets.delete_spreadsheet(user_id)

    # --- Новый, расширенный статус ----------------------
    def get_detailed_status(self, user_id: int):
        """Retrieves detailed statistics about the user's current goal.

        Args:
            user_id: The user's Telegram ID.

        Returns:
            A dictionary containing goal information and progress statistics.
        """
        stats = self.sheets.get_extended_statistics(user_id)
        goal_info = self.sheets.get_goal_info(user_id)
        return {
            "goal": goal_info.get("Глобальная цель", "—"),
            **stats,
        }

    # -----------------------------------------------------------------
    # Async-версия (использует sheets_async / llm_async, если доступны)
    # -----------------------------------------------------------------
    async def set_new_goal_async(
        self,
        user_id: int,
        goal_text: str,
        deadline_str: str,
        available_time_str: str,
    ) -> str:
        """Asynchronously creates a new goal, mirroring `set_new_goal`.

        Handles LLM rate limiting and uses async storage/LLM clients if available,
        otherwise falls back to running synchronous operations in an executor.

        Args:
            user_id: The user's Telegram ID.
            goal_text: The description of the goal.
            deadline_str: The deadline for the goal.
            available_time_str: The time available daily.

        Returns:
            The URL of the Google Spreadsheet.

        Raises:
            RateLimitException: If LLM call limit is exceeded.
        """
        import asyncio

        loop = asyncio.get_event_loop()

        # 1. clear data
        if self.sheets_async:
            await self.sheets_async.clear_user_data(user_id)  # type: ignore[attr-defined]
        else:
            await loop.run_in_executor(None, self._sync_sheets().clear_user_data, user_id)  # type: ignore[arg-type]

        # 1.5 Check rate limit for LLM
        try:
            self.llm_rate_limiter.check_limit(user_id)
        except RateLimitException as e:
            logger.warning(f"User {user_id} rate limited on generate_plan_async: {e}")
            LLM_API_CALLS.labels(
                method_name="generate_plan_async", status="ratelimited"
            ).inc()
            raise

        # 2. LLM generate plan
        if self.llm_async:
            plan_json = await self.llm_async.generate_plan(
                goal_text, deadline_str, available_time_str
            )
        else:
            plan_json = await loop.run_in_executor(None, self._sync_llm().generate_plan, goal_text, deadline_str, available_time_str)  # type: ignore[arg-type]

        today = datetime.now()
        full_plan = []
        for item in plan_json:
            day_offset = item["day"] - 1
            date = today + timedelta(days=day_offset)
            full_plan.append(
                {
                    COL_DATE: format_date(date),
                    COL_DAYOFWEEK: get_day_of_week(date),
                    COL_TASK: item["task"],
                    COL_STATUS: STATUS_NOT_DONE,
                }
            )

        goal_info = {
            "Глобальная цель": goal_text,
            "Срок выполнения": deadline_str,
            "Затраты в день": available_time_str,
            "Начало выполнения": format_date(today),
        }

        # 4. Save to sheets
        if self.sheets_async:
            spreadsheet_url = await self.sheets_async.save_goal_info(user_id, goal_info)  # type: ignore[arg-type]
            await self.sheets_async.save_plan(user_id, full_plan)  # type: ignore[arg-type]
        else:
            spreadsheet_url = await loop.run_in_executor(None, self._sync_sheets().save_goal_info, user_id, goal_info)  # type: ignore[arg-type]
            await loop.run_in_executor(None, self._sync_sheets().save_plan, user_id, full_plan)  # type: ignore[arg-type]

        GOALS_SET_TOTAL.inc()  # Increment goals set counter
        return spreadsheet_url

    # -------------------------------------------------
    # Новые async-версии часто вызываемых методов
    # -------------------------------------------------
    async def get_today_task_async(self, user_id: int) -> Any | None:
        """Asynchronously retrieves today's task, mirroring `get_today_task`.

        Uses async storage client if available, otherwise sync in executor.

        Args:
            user_id: The user's Telegram ID.

        Returns:
            Task dictionary or None.
        """
        import asyncio

        date_str = format_date(datetime.now())
        if self.sheets_async:
            return await self.sheets_async.get_task_for_date(user_id, date_str)  # type: ignore[attr-defined]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_sheets().get_task_for_date, user_id, date_str
        )

    async def update_today_task_status_async(self, user_id: int, status: str) -> None:
        """Asynchronously updates today's task status, mirroring `update_today_task_status`.

        Args:
            user_id: The user's Telegram ID.
            status: The new status string.
        """
        import asyncio

        date_str = format_date(datetime.now())
        if self.sheets_async:
            await self.sheets_async.update_task_status(user_id, date_str, status)  # type: ignore[attr-defined]
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self._sync_sheets().update_task_status, user_id, date_str, status
        )
        TASKS_STATUS_UPDATED_TOTAL.labels(new_status=status).inc()
        return  # Explicitly return None for void async method

    async def generate_motivation_message_async(self, user_id: int) -> str:
        """Asynchronously generates a motivation message, mirroring `generate_motivation_message`.

        Handles LLM rate limiting.

        Args:
            user_id: The user's Telegram ID.

        Returns:
            A motivational message string.

        Raises:
            RateLimitException: If LLM call limit is exceeded.
        """
        import asyncio

        if self.sheets_async:
            goal_info = await self.sheets_async.get_goal_info(user_id)  # type: ignore[attr-defined]
            stats = await self.sheets_async.get_statistics(user_id)  # type: ignore[attr-defined]
        else:
            loop = asyncio.get_event_loop()
            goal_info = await loop.run_in_executor(
                None, self._sync_sheets().get_goal_info, user_id
            )
            stats = await loop.run_in_executor(
                None, self._sync_sheets().get_statistics, user_id
            )

        # Check rate limit before LLM call
        try:
            self.llm_rate_limiter.check_limit(user_id)
        except RateLimitException as e:
            logger.warning(
                f"User {user_id} rate limited on generate_motivation_async: {e}"
            )
            LLM_API_CALLS.labels(
                method_name="generate_motivation_async", status="ratelimited"
            ).inc()
            raise

        if self.llm_async:
            return await self.llm_async.generate_motivation(
                goal_info.get("Глобальная цель", ""), stats
            )
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._sync_llm().generate_motivation,
            goal_info.get("Глобальная цель", ""),
            stats,
        )

    async def batch_update_task_statuses_async(
        self, user_id: int, updates: dict[str, str]
    ) -> None:
        """Asynchronously batch updates task statuses, mirroring `batch_update_task_statuses`.

        Args:
            user_id: The user's Telegram ID.
            updates: Dictionary of {date_string: status_string}.
        """
        import asyncio

        if self.sheets_async:
            await self.sheets_async.batch_update_task_statuses(user_id, updates)  # type: ignore[attr-defined]
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self._sync_sheets().batch_update_task_statuses, user_id, updates
        )

        for status_val in updates.values():  # Increment for each status updated
            TASKS_STATUS_UPDATED_TOTAL.labels(new_status=status_val).inc()
        return  # Explicitly return None for void async method

    # -------------------------------------------------
    # Новые async-версии дополнительных методов
    # -------------------------------------------------
    async def setup_user_async(self, user_id: int) -> None:
        """Asynchronously sets up the user, mirroring `setup_user`.

        Args:
            user_id: The user's Telegram ID.
        """
        import asyncio

        if self.sheets_async:
            await self.sheets_async.create_spreadsheet(user_id)  # type: ignore[attr-defined]
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_sheets().create_spreadsheet, user_id)  # type: ignore[arg-type]

    async def reset_user_async(self, user_id: int) -> None:
        """Asynchronously resets user data, mirroring `reset_user`.

        Args:
            user_id: The user's Telegram ID.
        """
        import asyncio

        if self.sheets_async:
            await self.sheets_async.delete_spreadsheet(user_id)  # type: ignore[attr-defined]
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_sheets().delete_spreadsheet, user_id)  # type: ignore[arg-type]

    async def get_detailed_status_async(self, user_id: int) -> Dict[str, Any]:
        """Asynchronously gets detailed status, mirroring `get_detailed_status`.

        Args:
            user_id: The user's Telegram ID.

        Returns:
            A dictionary with detailed goal and progress statistics.
        """
        import asyncio

        if self.sheets_async:
            stats = await self.sheets_async.get_extended_statistics(user_id)  # type: ignore[attr-defined]
            goal_info = await self.sheets_async.get_goal_info(user_id)  # type: ignore[attr-defined]
        else:
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(
                None, self._sync_sheets().get_extended_statistics, user_id
            )
            goal_info = await loop.run_in_executor(
                None, self._sync_sheets().get_goal_info, user_id
            )
        return {"goal": goal_info.get("Глобальная цель", "—"), **stats}

    # -------------------------------------------------
    # Internal helpers for static typing
    # -------------------------------------------------

    def _sync_sheets(self) -> StorageInterface:
        """Return synchronous SheetsManager, asserting it exists (for mypy)."""
        assert self.sheets_sync is not None
        return self.sheets_sync

    def _sync_llm(self) -> LLMInterface:
        """Return synchronous LLMInterface, asserting it exists (for mypy)."""
        assert self.llm_sync is not None
        return self.llm_sync
