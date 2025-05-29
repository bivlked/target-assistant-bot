"""Core logic for managing user goals, plans, and progress via LLM and storage."""

from __future__ import annotations

import structlog
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Final, Dict

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

if TYPE_CHECKING:  # Avoid import cycles
    pass

# Status string types (internal, for logic/metrics)
STATUS_NOT_DONE: Final[str] = "NOT_DONE"
STATUS_DONE: Final[str] = "DONE"
STATUS_PARTIAL: Final[str] = "PARTIALLY_DONE"

# User-facing status strings (for Sheets and display)
USER_FACING_STATUS_NOT_DONE: Final[str] = "Не выполнено"
USER_FACING_STATUS_DONE: Final[str] = "Выполнено"
USER_FACING_STATUS_PARTIAL: Final[str] = "Частично выполнено"

# Mapping for metrics: from Russian user-facing status to English internal status
RUSSIAN_TO_ENGLISH_STATUS_MAP: Final[Dict[str, str]] = {
    USER_FACING_STATUS_DONE: STATUS_DONE,
    USER_FACING_STATUS_NOT_DONE: STATUS_NOT_DONE,
    USER_FACING_STATUS_PARTIAL: STATUS_PARTIAL,
}

logger = structlog.get_logger(__name__)


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
    # API methods called from Telegram handlers
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
        # Clear previous data using legacy method
        goals = await self.storage.get_active_goals(user_id)
        for goal in goals:
            await self.storage.archive_goal(user_id, goal.goal_id)

        # 1.5 Check rate limit for LLM
        try:
            self.llm_rate_limiter.check_limit(user_id)
        except RateLimitException as e:
            logger.warning(
                "User rate limited on generate_plan", user_id=user_id, exc_info=e
            )
            LLM_API_CALLS.labels(
                method_name="generate_plan", status="ratelimited"
            ).inc()
            raise

        # 2. Generate plan via LLM
        plan_json = await self.llm.generate_plan(
            goal_text, deadline_str, available_time_str
        )

        # 3. Calculate dates
        today = datetime.now(timezone.utc)
        full_plan = []
        for item in plan_json:
            day_offset = item["day"] - 1
            date = today + timedelta(days=day_offset)
            full_plan.append(
                {
                    COL_DATE: format_date(date),
                    COL_DAYOFWEEK: get_day_of_week(date),
                    COL_TASK: item["task"],
                    COL_STATUS: USER_FACING_STATUS_NOT_DONE,  # Use Russian status for Sheets
                }
            )

        # 4. Save to Sheets
        goal_info = {
            "Глобальная цель": goal_text,  # Russian key for Sheets
            "Срок выполнения": deadline_str,  # Russian key for Sheets
            "Затраты в день": available_time_str,  # Russian key for Sheets
            "Начало выполнения": format_date(today),  # Russian key for Sheets
        }
        spreadsheet_url = await self.storage.save_goal_and_plan(
            user_id, goal_info, full_plan
        )

        GOALS_SET_TOTAL.inc()  # Increment goals set counter
        return spreadsheet_url

    async def get_today_task(self, user_id: int) -> Dict[str, Any] | None:
        """Asynchronously retrieves today's task."""
        return await self.storage.get_task_for_today(user_id)

    async def update_today_task_status(self, user_id: int, status: str) -> None:
        """Asynchronously updates the status of today's task.
        'status' is expected to be a Russian user-facing string.
        """
        date_str = format_date(datetime.now())
        # 'status' is already Russian, save it to Sheets as is
        await self.storage.update_task_status_old(user_id, date_str, status)

        # For metrics, map to English status
        english_status = RUSSIAN_TO_ENGLISH_STATUS_MAP.get(
            status, status
        )  # Fallback to original if not in map
        TASKS_STATUS_UPDATED_TOTAL.labels(new_status=english_status).inc()

    async def get_goal_status_details(self, user_id: int) -> str:
        """Asynchronously gets a brief string summary of goal progress."""
        return await self.storage.get_status_message(user_id)

    async def generate_motivation_message(self, user_id: int) -> str:
        """Asynchronously generates a motivational message."""
        try:
            self.llm_rate_limiter.check_limit(user_id)
        except RateLimitException as e:
            logger.warning(
                "User rate limited on generate_motivation", user_id=user_id, exc_info=e
            )
            LLM_API_CALLS.labels(
                method_name="generate_motivation", status="ratelimited"
            ).inc()
            raise

        goal_info = await self.storage.get_goal_info(user_id)
        stats = await self.storage.get_status_message(user_id)
        # Assuming goal_info and stats are dict-like or have .get()
        goal_text = (
            goal_info.get("Глобальная цель", "") if goal_info else ""
        )  # Russian key
        progress_summary = str(stats)  # Convert stats to string if it isn't already
        return await self.llm.generate_motivation(goal_text, progress_summary)

    # -------------------------------------------------
    # Reset
    # -------------------------------------------------
    async def reset_user(self, user_id: int) -> None:
        """Asynchronously deletes all user data."""
        await self.storage.delete_spreadsheet(user_id)

    # --- New, extended status ----------------------
    async def get_detailed_status(self, user_id: int) -> Dict[str, Any]:
        """Asynchronously gets detailed statistics about the user's current goal."""
        stats = await self.storage.get_extended_statistics(user_id)
        goal_info = await self.storage.get_goal_info(user_id)
        return {
            "goal": (
                goal_info.get("Глобальная цель", "—") if goal_info else "—"
            ),  # Russian key
            **stats,
        }

    # -----------------------------------------------------------------
    # Async version (uses sheets_async / llm_async, if available)
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
        'updates' dict values are expected to be Russian user-facing strings.

        Also, increments the TASKS_STATUS_UPDATED_TOTAL metric for each status update.
        """
        # Convert to new format expected by interface
        new_updates = {}
        for date_str, status in updates.items():
            # Assume goal_id 1 for legacy compatibility
            new_updates[(1, date_str)] = status

        await self.storage.batch_update_task_statuses(user_id, new_updates)

        # For metrics, map to English statuses
        for status_val in updates.values():  # status_val is Russian
            english_status_val = RUSSIAN_TO_ENGLISH_STATUS_MAP.get(
                status_val, status_val
            )  # Fallback
            TASKS_STATUS_UPDATED_TOTAL.labels(new_status=english_status_val).inc()
