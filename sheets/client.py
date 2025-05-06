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
    def __init__(self):
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
    def create_spreadsheet(self, user_id: int):
        sh = self._get_spreadsheet(user_id)
        try:
            sh.share("", perm_type="anyone", role="writer", with_link=True)
        except Exception:
            pass

    @RETRY
    def clear_user_data(self, user_id: int):
        sh = self._get_spreadsheet(user_id)
        for title in (GOAL_INFO_SHEET, PLAN_SHEET):
            try:
                ws = sh.worksheet(title)
            except gspread.WorksheetNotFound:
                ws = sh.add_worksheet(title=title, rows=10, cols=3 if title == GOAL_INFO_SHEET else 4)
            ws.clear()

    @RETRY
    def save_goal_info(self, user_id: int, goal_data: dict[str, str]) -> str:
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
        return sh.url

    @RETRY
    def save_plan(self, user_id: int, plan: List[dict[str, Any]]):
        sh = self._get_spreadsheet(user_id)
        ws = sh.worksheet(PLAN_SHEET)
        header = [list(PLAN_HEADERS)]
        rows = [[p[COL_DATE], p[COL_DAYOFWEEK], p[COL_TASK], p[COL_STATUS]] for p in plan]
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

    @RETRY
    def get_goal_info(self, user_id: int):
        ws = self._get_spreadsheet(user_id).worksheet(GOAL_INFO_SHEET)
        data = ws.get_all_values()
        return {row[0]: row[1] for row in data if row}

    @RETRY
    def get_task_for_date(self, user_id: int, target_date: str):
        ws = self._get_spreadsheet(user_id).worksheet(PLAN_SHEET)
        for row in ws.get_all_records():
            if row.get(COL_DATE) == target_date:
                return row
        return None

    @RETRY
    def update_task_status(self, user_id: int, target_date: str, status: str):
        ws = self._get_spreadsheet(user_id).worksheet(PLAN_SHEET)
        data = ws.get_all_records()
        for idx, row in enumerate(data, start=2):
            if row.get(COL_DATE) == target_date:
                ws.update_cell(idx, 4, status)
                break

    @RETRY
    def get_statistics(self, user_id: int):
        ws = self._get_spreadsheet(user_id).worksheet(PLAN_SHEET)
        data = ws.get_all_records()
        total = len(data)
        done = sum(1 for r in data if r[COL_STATUS] == "Выполнено")
        percent = int(done / total * 100) if total else 0
        remaining = total - done
        return f"Выполнено {done} из {total} ({percent}%), осталось {remaining} дней"

    @RETRY
    def delete_spreadsheet(self, user_id: int):
        name = f"TargetAssistant_{user_id}"
        try:
            sh = self.gc.open(name)
            self.gc.del_spreadsheet(sh.id)
        except gspread.SpreadsheetNotFound:
            return

    # --- batch update statuses ---
    @RETRY
    def batch_update_task_statuses(self, user_id: int, updates: dict[str, str]):
        """Обновляет статусы нескольких дат одной операцией."""
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
