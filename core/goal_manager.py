from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

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
    """Бизнес-логика с поддержкой sync и async клиентов."""

    def __init__(
        self,
        sheets_sync: "SheetsManager | None" = None,
        llm_sync: "LLMClient | None" = None,
        sheets_async: "AsyncSheetsManager | None" = None,
        llm_async: "AsyncLLMClient | None" = None,
    ):
        if not (sheets_sync or sheets_async):
            raise ValueError("Требуется sheets_sync или sheets_async")
        if not (llm_sync or llm_async):
            raise ValueError("Требуется llm_sync или llm_async")

        # сохраняем
        self.sheets_sync = sheets_sync
        self.sheets_async = sheets_async
        self.llm_sync = llm_sync
        self.llm_async = llm_async

        # для существующего кода остаётся общий атрибут
        self.sheets = sheets_sync or sheets_async  # type: ignore[assignment]
        self.llm = llm_sync or llm_async  # type: ignore[assignment]

    # -------------------------------------------------
    # Методы API, вызываемые из Telegram-обработчиков
    # -------------------------------------------------
    def setup_user(self, user_id: int) -> None:
        self.sheets.create_spreadsheet(user_id)

    def set_new_goal(
        self,
        user_id: int,
        goal_text: str,
        deadline_str: str,
        available_time_str: str,
    ) -> str:
        """Создает новую цель пользователя. Возвращает ссылку на таблицу."""
        # 1. Очищаем предыдущие листы
        self.sheets.clear_user_data(user_id)

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
        return spreadsheet_url

    def get_today_task(self, user_id: int):
        date_str = format_date(datetime.now())
        return self.sheets.get_task_for_date(user_id, date_str)

    def update_today_task_status(self, user_id: int, status: str):
        date_str = format_date(datetime.now())
        self.sheets.update_task_status(user_id, date_str, status)

    def get_goal_status_details(self, user_id: int):
        # Старая строковая статистика (для совместимости)
        return self.sheets.get_statistics(user_id)

    def generate_motivation_message(self, user_id: int):
        goal_info = self.sheets.get_goal_info(user_id)
        stats = self.sheets.get_statistics(user_id)
        return self.llm.generate_motivation(goal_info.get("Глобальная цель", ""), stats)

    # -------------------------------------------------
    # Сброс
    # -------------------------------------------------
    def reset_user(self, user_id: int):
        self.sheets.delete_spreadsheet(user_id)

    # --- Новый, расширенный статус ----------------------
    def get_detailed_status(self, user_id: int):
        """Возвращает подробную статистику, аналоги /status у второй команды."""
        stats = self.sheets.get_extended_statistics(user_id)
        goal_info = self.sheets.get_goal_info(user_id)
        return {
            "goal": goal_info.get("Глобальная цель", "—"),
            **stats,
        } 