from __future__ import annotations

import logging
from typing import Any, List

import gspread  # type: ignore
from google.oauth2.service_account import Credentials  # type: ignore
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)
from gspread.exceptions import APIError  # type: ignore

from config import google
from utils.cache import cached_sheet_method, invalidate_sheet_cache
from core.metrics import SHEETS_API_CALLS, SHEETS_API_LATENCY
from utils.retry_decorators import retry_google_sheets
import time

logger = logging.getLogger(__name__)

# -- Названия листов (рус.) --
GOAL_INFO_SHEET = "Информация о цели"
PLAN_SHEET = "План"

# -- Заголовки колонок для листа План --
COL_DATE = "Дата"
COL_DAYOFWEEK = "День недели"
COL_TASK = "Задача"
COL_STATUS = "Статус"

# Для импорта другими модулями
PLAN_HEADERS = (COL_DATE, COL_DAYOFWEEK, COL_TASK, COL_STATUS)

RETRY = retry(
    retry=retry_if_exception_type(APIError),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
)


class SheetsManager:
    """Synchronous client for interacting with Google Sheets.

    This class encapsulates all domain-specific logic for managing user spreadsheets,
    including creating/opening sheets, reading/writing goal and plan data,
    formatting cells, and calculating statistics. It uses the `gspread` library
    for Google Sheets API communication and `tenacity` for retrying operations
    in case of API errors or network issues. It also integrates with `SheetCache`
    for caching read operations and `Prometheus` for metrics.

    Implements the `StorageInterface` protocol.
    """

    def __init__(self):
        """Initializes the gspread client and authenticates with Google API.

        Service account credentials are read from `config.google.credentials_path`.
        Scopes for both Google Sheets and Google Drive are requested to allow
        sharing spreadsheets via `gspread.Spreadsheet.share`.
        """
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(
            google.credentials_path, scopes=scopes
        )
        self.gc = gspread.authorize(creds)

    # -------------------------------------------------
    # Вспомогательные методы
    # -------------------------------------------------
    def _get_spreadsheet(self, user_id: int):
        name = f"TargetAssistant_{user_id}"
        try:
            sh = self.gc.open(name)
            try:
                sh.share("", perm_type="anyone", role="writer", with_link=True)
            except Exception:
                pass
            try:
                rename_map = {
                    "Цель": GOAL_INFO_SHEET,
                    "GoalInfo": GOAL_INFO_SHEET,
                    "Plan": PLAN_SHEET,
                }
                for old, new in rename_map.items():
                    try:
                        ws_old = sh.worksheet(old)
                        if ws_old.title != new:
                            ws_old.update_title(new)
                    except gspread.WorksheetNotFound:
                        pass
                for title, rows, cols in (
                    (GOAL_INFO_SHEET, 10, 3),
                    (PLAN_SHEET, 400, 4),
                ):
                    try:
                        sh.worksheet(title)
                    except gspread.WorksheetNotFound:
                        sh.add_worksheet(title=title, rows=rows, cols=cols)
            except Exception as e:
                logger.warning("Ошибка проверки/переименования листов: %s", e)
            return sh
        except gspread.SpreadsheetNotFound:
            sh = self.gc.create(name)
            sh.add_worksheet(title=GOAL_INFO_SHEET, rows=10, cols=3)
            sh.add_worksheet(title=PLAN_SHEET, rows=400, cols=4)
            try:
                sh.del_worksheet(sh.sheet1)
            except Exception:
                pass
            try:
                sh.share("", perm_type="anyone", role="writer", with_link=True)
            except Exception as e:
                logger.warning("Не удалось открыть доступ: %s", e)
            return sh

    # -------------------------------------------------
    # Публичные методы
    # -------------------------------------------------
    # No cache for create_spreadsheet: it modifies and must be fresh
    def create_spreadsheet(self, user_id: int):
        """Creates (if not exists) or opens a user's spreadsheet and ensures it's shared.

        Args:
            user_id: The Telegram ID of the user.

        Note: This operation is not cached as it always involves potential modification
              or ensuring fresh access permissions.
        """
        method_name = "create_spreadsheet"
        start_time = time.monotonic()
        sh = self._get_spreadsheet(user_id)
        try:
            sh.share("", perm_type="anyone", role="writer", with_link=True)
        except Exception:
            pass

        SHEETS_API_CALLS.labels(method_name=method_name, operation_type="write").inc()
        SHEETS_API_LATENCY.labels(method_name=method_name).observe(
            time.monotonic() - start_time
        )
        # invalidate cache
        invalidate_sheet_cache(user_id)

    @retry_google_sheets
    def clear_user_data(self, user_id: int):
        """Clears all data from the user's 'Goal Info' and 'Plan' sheets.

        The spreadsheet structure (sheets themselves) is preserved.

        Args:
            user_id: The Telegram ID of the user.
        """
        method_name = "clear_user_data"
        start_time = time.monotonic()
        sh = self._get_spreadsheet(user_id)
        for title in (GOAL_INFO_SHEET, PLAN_SHEET):
            try:
                ws = sh.worksheet(title)
            except gspread.WorksheetNotFound:
                ws = sh.add_worksheet(
                    title=title, rows=10, cols=3 if title == GOAL_INFO_SHEET else 4
                )
            ws.clear()

        SHEETS_API_CALLS.labels(method_name=method_name, operation_type="write").inc()
        SHEETS_API_LATENCY.labels(method_name=method_name).observe(
            time.monotonic() - start_time
        )
        # invalidate cache
        invalidate_sheet_cache(user_id)

    @retry_google_sheets
    def save_goal_info(self, user_id: int, goal_data: dict[str, str]) -> str:
        """Saves goal information to the 'Goal Info' sheet and formats it.

        Args:
            user_id: The Telegram ID of the user.
            goal_data: A dictionary containing goal parameters (e.g.,
                       {"Global Goal": "Learn Python", "Deadline": "3 months"}).

        Returns:
            The URL of the user's spreadsheet.
        """
        method_name = "save_goal_info"
        start_time = time.monotonic()
        sh = self._get_spreadsheet(user_id)
        ws = sh.worksheet(GOAL_INFO_SHEET)
        rows = [[k, v, ""] for k, v in goal_data.items()]
        ws.update("A1", rows)
        try:
            ws.format("A:A", {"textFormat": {"bold": True}})
            if hasattr(ws, "columns_auto_resize"):
                ws.columns_auto_resize(1, 3)
        except Exception:
            pass

        SHEETS_API_CALLS.labels(method_name=method_name, operation_type="write").inc()
        SHEETS_API_LATENCY.labels(method_name=method_name).observe(
            time.monotonic() - start_time
        )
        # invalidate cache
        invalidate_sheet_cache(user_id)

        return sh.url

    @retry_google_sheets
    @cached_sheet_method(lambda: "goal_info")
    def get_goal_info(self, user_id: int):
        """Retrieves goal parameters from the 'Goal Info' sheet.

        This method is cached.

        Args:
            user_id: The Telegram ID of the user.

        Returns:
            A dictionary where keys are parameter names (e.g., "Global Goal")
            and values are their corresponding string values.
            Example: {
                "Global Goal": "Learn Python",
                "Deadline": "3 months",
                "Daily Commitment": "1 hour"
            }
        """
        method_name = "get_goal_info"
        start_time = time.monotonic()
        ws = self._get_spreadsheet(user_id).worksheet(GOAL_INFO_SHEET)
        data = ws.get_all_values()
        result = {row[0]: row[1] for row in data if row}
        SHEETS_API_CALLS.labels(method_name=method_name, operation_type="read").inc()
        SHEETS_API_LATENCY.labels(method_name=method_name).observe(
            time.monotonic() - start_time
        )
        return result

    @retry_google_sheets
    @cached_sheet_method(lambda target_date: target_date)
    def get_task_for_date(self, user_id: int, target_date: str):
        """Finds and returns a task for a specific date from the 'Plan' sheet.

        This method is cached based on `user_id` and `target_date`.

        Args:
            user_id: The Telegram ID of the user.
            target_date: The date string to search for (e.g., "dd.mm.yyyy").

        Returns:
            A dictionary representing the task row if found, otherwise None.
        """
        method_name = "get_task_for_date"
        start_time = time.monotonic()
        ws = self._get_spreadsheet(user_id).worksheet(PLAN_SHEET)
        for row in ws.get_all_records():
            if row.get(COL_DATE) == target_date:
                SHEETS_API_CALLS.labels(
                    method_name=method_name, operation_type="read"
                ).inc()
                SHEETS_API_LATENCY.labels(method_name=method_name).observe(
                    time.monotonic() - start_time
                )
                return row
        SHEETS_API_CALLS.labels(method_name=method_name, operation_type="read").inc()
        SHEETS_API_LATENCY.labels(method_name=method_name).observe(
            time.monotonic() - start_time
        )
        return None

    @retry_google_sheets
    def update_task_status(self, user_id: int, target_date: str, status: str):
        """Updates the 'Status' field of a task for a specific date.

        Args:
            user_id: The Telegram ID of the user.
            target_date: The date string of the task to update.
            status: The new status string for the task.
        """
        method_name = "update_task_status"
        start_time = time.monotonic()
        ws = self._get_spreadsheet(user_id).worksheet(PLAN_SHEET)
        data = ws.get_all_records()
        for idx, row in enumerate(data, start=2):
            if row.get(COL_DATE) == target_date:
                ws.update_cell(idx, 4, status)
                break

        # invalidate cache
        invalidate_sheet_cache(user_id)

    @retry_google_sheets
    @cached_sheet_method(lambda: "statistics")
    def get_statistics(self, user_id: int):
        """Generates a brief string summary of the user's plan execution statistics.

        This method is cached.

        Args:
            user_id: The Telegram ID of the user.

        Returns:
            A human-readable string summarizing the progress (e.g., "Completed 5 of 30 (16%), 25 days left").
        """
        method_name = "get_statistics"
        start_time = time.monotonic()
        ws = self._get_spreadsheet(user_id).worksheet(PLAN_SHEET)
        data = ws.get_all_records()
        total = len(data)
        done = sum(1 for r in data if r[COL_STATUS] == "Выполнено")
        percent = int(done / total * 100) if total else 0
        remaining = total - done
        return f"Выполнено {done} из {total} ({percent}%), осталось {remaining} дней"

    @retry_google_sheets
    def delete_spreadsheet(self, user_id: int):
        """Permanently deletes the user's spreadsheet from Google Drive.

        Args:
            user_id: The Telegram ID of the user whose spreadsheet is to be deleted.
        """
        method_name = "delete_spreadsheet"
        start_time = time.monotonic()
        name = f"TargetAssistant_{user_id}"
        try:
            sh = self.gc.open(name)
            self.gc.del_spreadsheet(sh.id)
        except gspread.SpreadsheetNotFound:
            return
        finally:
            # invalidate cache
            invalidate_sheet_cache(user_id)

    # --- batch update statuses ---
    @retry_google_sheets
    def batch_update_task_statuses(self, user_id: int, updates: dict[str, str]):
        """Batch updates task statuses for multiple dates in a single operation.

        This method reads all records once to map dates to row numbers, then performs
        a single `batch_update` call to modify cell values, making it efficient
        in terms of API calls.

        Args:
            user_id: The Telegram ID of the user.
            updates: A dictionary where keys are date strings and values are new status strings.
        """
        method_name = "batch_update_task_statuses"
        start_time = time.monotonic()
        ws = self._get_spreadsheet(user_id).worksheet(PLAN_SHEET)
        data = ws.get_all_records()
        row_map: dict[str, int] = {}
        for idx, row in enumerate(data, start=2):
            dt = row.get(COL_DATE)
            if dt:
                row_map[dt] = idx
        for date_str, status in updates.items():
            row_idx = row_map.get(date_str)
            if row_idx:
                ws.update_cell(row_idx, 4, status)

        # invalidate cache
        invalidate_sheet_cache(user_id)

    # --- Дополнительные методы статистики и форматирования ------------------
    @retry_google_sheets
    @cached_sheet_method(lambda: "spreadsheet_url")
    def get_spreadsheet_url(self, user_id: int) -> str:
        """Returns the URL of the user's spreadsheet, creating it if necessary.

        This method is cached.

        Args:
            user_id: The Telegram ID of the user.

        Returns:
            The URL string of the Google Spreadsheet.
        """
        method_name = "get_spreadsheet_url"
        start_time = time.monotonic()
        sh = self._get_spreadsheet(user_id)
        SHEETS_API_CALLS.labels(method_name=method_name, operation_type="read").inc()
        SHEETS_API_LATENCY.labels(method_name=method_name).observe(
            time.monotonic() - start_time
        )
        return sh.url

    @retry_google_sheets
    @cached_sheet_method(
        lambda *a, **kw: f"extended_stats:{kw.get('upcoming_count', a[0] if a else 5)}"
    )
    def get_extended_statistics(self, user_id: int, upcoming_count: int = 5):
        """Retrieves detailed progress statistics and a list of upcoming tasks.

        This method is cached based on `user_id` and `upcoming_count`.

        Args:
            user_id: The Telegram ID of the user.
            upcoming_count: The number of upcoming tasks to retrieve (default is 5).

        Returns:
            A dictionary containing detailed progress statistics and a list of upcoming tasks.
        """
        """Подробная статистика прогресса + ближайшие задачи.

        Возвращает dict с ключами total_days, completed_days, progress_percent,
        days_passed, days_left, upcoming_tasks (список), sheet_url.
        """
        sh = self._get_spreadsheet(user_id)
        ws_plan = sh.worksheet(PLAN_SHEET)

        plan_rows = ws_plan.get_all_records()
        total_days = len(plan_rows)
        completed_days = sum(1 for r in plan_rows if r.get(COL_STATUS) == "Выполнено")
        progress_percent = int(completed_days / total_days * 100) if total_days else 0

        # --- работа с датами
        from datetime import datetime as _dt
        from utils.helpers import (
            format_date as _fmt,
        )  # локальный импорт, чтобы избежать циклов

        def _parse(date_str: str):
            for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
                try:
                    return _dt.strptime(date_str, fmt)
                except ValueError:
                    continue
            return None

        today_dt = _dt.strptime(_fmt(_dt.now()), "%d.%m.%Y")

        days_passed = sum(
            1
            for r in plan_rows
            if _parse(r.get(COL_DATE, "")) and _parse(r.get(COL_DATE)) < today_dt
        )
        days_left = total_days - days_passed

        upcoming = [
            r
            for r in plan_rows
            if _parse(r.get(COL_DATE, "")) and _parse(r.get(COL_DATE)) >= today_dt
        ]
        upcoming_sorted = sorted(upcoming, key=lambda r: _parse(r.get(COL_DATE)))[
            :upcoming_count
        ]

        return {
            "total_days": total_days,
            "completed_days": completed_days,
            "progress_percent": progress_percent,
            "days_passed": days_passed,
            "days_left": days_left,
            "upcoming_tasks": upcoming_sorted,
            "sheet_url": sh.url,
        }

    # Форматирование Goal sheet после сохранения
    @retry_google_sheets
    def _format_goal_sheet(self, user_id: int):
        """Applies formatting (bold font, column auto-resize) to the 'Goal Info' sheet.

        This is an internal helper method, typically called after saving goal info.

        Args:
            user_id: The Telegram ID of the user.
        """
        try:
            sh = self._get_spreadsheet(user_id)
            ws = sh.worksheet(GOAL_INFO_SHEET)
            ws.format("A:A", {"textFormat": {"bold": True}})
            if hasattr(ws, "columns_auto_resize"):
                ws.columns_auto_resize(1, 3)
        except Exception:
            pass

    @retry_google_sheets
    def save_plan(self, user_id: int, plan: List[dict[str, Any]]) -> None:
        """Сохраняет список ежедневных задач в лист *План* и форматирует шапку."""
        try:
            sh = self._get_spreadsheet(user_id)
            ws = sh.worksheet(PLAN_SHEET)
            header = [list(PLAN_HEADERS)]
            rows = [
                [p[COL_DATE], p[COL_DAYOFWEEK], p[COL_TASK], p[COL_STATUS]]
                for p in plan
            ]
            ws.update("A1", header + rows)
            try:
                ws.format(
                    "A1:D1",
                    {
                        "textFormat": {"bold": True},
                        "horizontalAlignment": "CENTER",
                        "backgroundColor": {"red": 1, "green": 0.898, "blue": 0.8},
                    },
                )
                ws.format("A:A", {"horizontalAlignment": "CENTER"})
            except Exception:
                pass
            if hasattr(ws, "columns_auto_resize"):
                try:
                    ws.columns_auto_resize(1, 4)
                except Exception:
                    pass
            try:
                if hasattr(ws, "freeze"):
                    ws.freeze(rows=1)
            except Exception:
                pass
        finally:
            invalidate_sheet_cache(user_id)
