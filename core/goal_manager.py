from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, cast, Any

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

        # keep raw refs
        self.sheets_sync = sheets_sync
        self.sheets_async = sheets_async
        self.llm_sync = llm_sync
        self.llm_async = llm_async

        # These attributes are used both in sync and async context; exact concrete type
        # is not important at runtime, поэтому указываем Any, чтобы избежать NameError
        # из-за отсутствия реального класса, когда импорт находится под TYPE_CHECKING.
        self.sheets: Any = sheets_sync or sheets_async
        self.llm: Any = llm_sync or llm_async

    # -------------------------------------------------
    # Методы API, вызываемые из Telegram-обработчиков
    # -------------------------------------------------
    def setup_user(self, user_id: int) -> None:
        """Создаёт (или открывает) Google-таблицу для пользователя.

        Метод вызывается хендлером `/start` для первичной инициализации
        инфраструктуры. Если таблица уже существует, она просто будет
        открыта. Сам объект *GoalManager* проксирует вызов к
        ``SheetsManager.create_spreadsheet`` (или его async-варианту).

        Параметры
        ----------
        user_id: int
            Telegram-ID пользователя, по которому формируется уникальное
            имя таблицы вида ``TargetAssistant_<user_id>``.
        """
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
        """Возвращает задачу, запланированную на текущий день."""
        date_str = format_date(datetime.now())
        return self.sheets.get_task_for_date(user_id, date_str)

    def update_today_task_status(self, user_id: int, status: str):
        """Отмечает статус сегодняшней задачи.

        Аргументы
        ---------
        user_id: int
            Telegram-ID пользователя.
        status: str
            Строка-метка из ``STATUS_*`` (например, «Выполнено»).
        """
        date_str = format_date(datetime.now())
        self.sheets.update_task_status(user_id, date_str, status)

    def get_goal_status_details(self, user_id: int):
        """Краткая строковая статистика прогресса (совместимость)."""
        # Старая строковая статистика (для совместимости)
        return self.sheets.get_statistics(user_id)

    def generate_motivation_message(self, user_id: int):
        """Генерирует мотивирующее сообщение через LLM."""
        goal_info = self.sheets.get_goal_info(user_id)
        stats = self.sheets.get_statistics(user_id)
        return self.llm.generate_motivation(goal_info.get("Глобальная цель", ""), stats)

    # -------------------------------------------------
    # Сброс
    # -------------------------------------------------
    def reset_user(self, user_id: int):
        """Полностью удаляет Google-таблицу пользователя."""
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
        """Асинхронная версия создания новой цели."""

        import asyncio

        loop = asyncio.get_event_loop()

        # 1. clear data
        if self.sheets_async:
            await self.sheets_async.clear_user_data(user_id)  # type: ignore[attr-defined]
        else:
            await loop.run_in_executor(None, self.sheets_sync.clear_user_data, user_id)  # type: ignore[arg-type]

        # 2. LLM generate plan
        if self.llm_async:
            plan_json = await self.llm_async.generate_plan(goal_text, deadline_str, available_time_str)  # type: ignore[attr-defined]
        else:
            plan_json = await loop.run_in_executor(None, self.llm_sync.generate_plan, goal_text, deadline_str, available_time_str)  # type: ignore[arg-type]

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
            spreadsheet_url = await loop.run_in_executor(None, self.sheets_sync.save_goal_info, user_id, goal_info)  # type: ignore[arg-type]
            await loop.run_in_executor(None, self.sheets_sync.save_plan, user_id, full_plan)  # type: ignore[arg-type]

        return spreadsheet_url

    # -------------------------------------------------
    # Новые async-версии часто вызываемых методов
    # -------------------------------------------------
    async def get_today_task_async(self, user_id: int):  # noqa: D401
        """Асинхронная версия get_today_task.

        Использует sheets_async, если он инициализирован, иначе запускает
        синхронный метод в executor, чтобы не блокировать event loop.
        """
        import asyncio

        date_str = format_date(datetime.now())
        if self.sheets_async:
            return await self.sheets_async.get_task_for_date(user_id, date_str)  # type: ignore[attr-defined]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.sheets_sync.get_task_for_date, user_id, date_str  # type: ignore[arg-type]
        )

    async def update_today_task_status_async(
        self, user_id: int, status: str
    ):  # noqa: D401
        """Асинхронная версия update_today_task_status."""
        import asyncio

        date_str = format_date(datetime.now())
        if self.sheets_async:
            await self.sheets_async.update_task_status(user_id, date_str, status)  # type: ignore[attr-defined]
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self.sheets_sync.update_task_status, user_id, date_str, status  # type: ignore[arg-type]
        )

    async def generate_motivation_message_async(self, user_id: int):  # noqa: D401
        """Асинхронная версия generate_motivation_message."""
        import asyncio

        if self.sheets_async:
            goal_info = await self.sheets_async.get_goal_info(user_id)  # type: ignore[attr-defined]
            stats = await self.sheets_async.get_statistics(user_id)  # type: ignore[attr-defined]
        else:
            loop = asyncio.get_event_loop()
            goal_info = await loop.run_in_executor(None, self.sheets_sync.get_goal_info, user_id)  # type: ignore[arg-type]
            stats = await loop.run_in_executor(None, self.sheets_sync.get_statistics, user_id)  # type: ignore[arg-type]

        if self.llm_async:
            return await self.llm_async.generate_motivation(
                goal_info.get("Глобальная цель", ""), stats  # type: ignore[attr-defined]
            )
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.llm_sync.generate_motivation,
            goal_info.get("Глобальная цель", ""),
            stats,
        )  # type: ignore[arg-type]

    async def batch_update_task_statuses_async(
        self, user_id: int, updates: dict[str, str]
    ):
        """Пакетное обновление статусов (используется /check)."""
        import asyncio

        if self.sheets_async:
            await self.sheets_async.batch_update_task_statuses(user_id, updates)  # type: ignore[attr-defined]
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.sheets_sync.batch_update_task_statuses, user_id, updates)  # type: ignore[arg-type]

    # -------------------------------------------------
    # Новые async-версии дополнительных методов
    # -------------------------------------------------
    async def setup_user_async(self, user_id: int):  # noqa: D401
        """Асинхронная версия setup_user."""
        import asyncio

        if self.sheets_async:
            await self.sheets_async.create_spreadsheet(user_id)  # type: ignore[attr-defined]
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.sheets_sync.create_spreadsheet, user_id)  # type: ignore[arg-type]

    async def reset_user_async(self, user_id: int):  # noqa: D401
        """Асинхронная версия :py:meth:`reset_user`."""
        import asyncio

        if self.sheets_async:
            await self.sheets_async.delete_spreadsheet(user_id)  # type: ignore[attr-defined]
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.sheets_sync.delete_spreadsheet, user_id)  # type: ignore[arg-type]

    async def get_detailed_status_async(self, user_id: int):  # noqa: D401
        """Асинхронная версия get_detailed_status."""
        import asyncio

        if self.sheets_async:
            stats = await self.sheets_async.get_extended_statistics(user_id)  # type: ignore[attr-defined]
            goal_info = await self.sheets_async.get_goal_info(user_id)  # type: ignore[attr-defined]
        else:
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(None, self.sheets_sync.get_extended_statistics, user_id)  # type: ignore[arg-type]
            goal_info = await loop.run_in_executor(None, self.sheets_sync.get_goal_info, user_id)  # type: ignore[arg-type]
        return {"goal": goal_info.get("Глобальная цель", "—"), **stats}
