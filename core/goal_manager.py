from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional, Final, cast, List, Dict

from utils.helpers import format_date, get_day_of_week
from sheets.client import COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS

from core.interfaces import AsyncStorageInterface, AsyncLLMInterface
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
    """Asynchronously manages user goals, tasks, and interactions.

    Orchestrates operations with storage (e.g., Google Sheets via AsyncStorageInterface)
    and LLM (e.g., OpenAI via AsyncLLMInterface) for planning and motivation.
    All public methods are asynchronous.
    """

    def __init__(
        self,
        storage: AsyncStorageInterface,
        llm: AsyncLLMInterface,
    ):
        """Initializes GoalManager with async storage and LLM clients."""
        self.storage = storage
        self.llm = llm

        # Initialize rate limiter for LLM calls
        self.llm_rate_limiter = UserRateLimiter(
            default_tokens_per_second=ratelimiter_cfg.llm_requests_per_minute / 60.0,
            default_max_tokens=float(ratelimiter_cfg.llm_max_burst),
        )

    # -------------------------------------------------
    # Методы API, вызываемые из Telegram-обработчиков
    # -------------------------------------------------
    async def setup_user(self, user_id: int) -> None:
        """Asynchronously sets up the user by creating/opening their Google Spreadsheet."""
        await self.storage.create_spreadsheet(user_id)

    async def set_new_goal(
        self,
        user_id: int,
        goal_text: str,
        deadline_str: str,
        available_time_str: str,
    ) -> str:
        """Asynchronously sets a new goal, generates a plan, and saves all data."""
        await self.storage.clear_user_data(user_id)

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
        plan_json = await self.llm.generate_plan(
            goal_text, deadline_str, available_time_str
        )

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
        spreadsheet_url = await self.storage.save_goal_info(user_id, goal_info)
        await self.storage.save_plan(user_id, full_plan)

        GOALS_SET_TOTAL.inc()  # Increment goals set counter
        return spreadsheet_url

    async def get_today_task(self, user_id: int) -> Dict[str, Any] | None:
        """Asynchronously retrieves today's task."""
        date_str = format_date(datetime.now())
        return await self.storage.get_task_for_date(user_id, date_str)

    async def update_today_task_status(self, user_id: int, status: str) -> None:
        """Asynchronously updates the status of today's task."""
        date_str = format_date(datetime.now())
        await self.storage.update_task_status(user_id, date_str, status)
        TASKS_STATUS_UPDATED_TOTAL.labels(new_status=status).inc()

    async def get_goal_status_details(self, user_id: int) -> str:
        """Asynchronously gets a brief string summary of goal progress."""
        return await self.storage.get_statistics(user_id)

    async def generate_motivation_message(self, user_id: int) -> str:
        """Asynchronously generates a motivational message."""
        try:
            self.llm_rate_limiter.check_limit(user_id)
        except RateLimitException as e:
            logger.warning(f"User {user_id} rate limited on generate_motivation: {e}")
            LLM_API_CALLS.labels(
                method_name="generate_motivation", status="ratelimited"
            ).inc()
            raise

        goal_info = await self.storage.get_goal_info(user_id)
        stats = await self.storage.get_statistics(user_id)
        # Assuming goal_info and stats are dict-like or have .get()
        goal_text = goal_info.get("Глобальная цель", "") if goal_info else ""
        progress_summary = str(stats)  # Convert stats to string if it isn't already
        return await self.llm.generate_motivation(goal_text, progress_summary)

    # -------------------------------------------------
    # Сброс
    # -------------------------------------------------
    async def reset_user(self, user_id: int) -> None:
        """Asynchronously deletes all user data."""
        await self.storage.delete_spreadsheet(user_id)

    # --- Новый, расширенный статус ----------------------
    async def get_detailed_status(self, user_id: int) -> Dict[str, Any]:
        """Asynchronously gets detailed statistics about the user's current goal."""
        stats = await self.storage.get_extended_statistics(user_id)
        goal_info = await self.storage.get_goal_info(user_id)
        return {
            "goal": goal_info.get("Глобальная цель", "—") if goal_info else "—",
            **stats,
        }

    # -----------------------------------------------------------------
    # Async-версия (использует sheets_async / llm_async, если доступны)
    # -----------------------------------------------------------------
    # All methods are now async directly. The specific async_ versions were removed.

    # -------------------------------------------------
    # Internal helpers for static typing
    # -------------------------------------------------
    # Synchronous helper methods are no longer needed as the class is fully async.

    async def batch_update_task_statuses(
        self, user_id: int, updates: Dict[str, str]
    ) -> None:
        """Asynchronously batch updates task statuses via the storage interface.

        Also, increments the TASKS_STATUS_UPDATED_TOTAL metric for each status update.
        """
        await self.storage.batch_update_task_statuses(user_id, updates)
        for status_val in updates.values():  # Increment for each status updated
            TASKS_STATUS_UPDATED_TOTAL.labels(new_status=status_val).inc()
