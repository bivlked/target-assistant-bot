from __future__ import annotations

import logging
from typing import Any, List

import gspread  # type: ignore
from google.oauth2.service_account import Credentials  # type: ignore
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from gspread.exceptions import APIError  # type: ignore

from config import google

logger = logging.getLogger(__name__)

# Константы названий листов
GOAL_INFO_SHEET = "GoalInfo"
PLAN_SHEET = "Plan"

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
        creds = Credentials.from_service_account_file(google.credentials_path, scopes=scopes)
        self.gc = gspread.authorize(creds)

    # -------------------------------------------------
    # Вспомогательные методы
    # -------------------------------------------------
    def _get_spreadsheet(self, user_id: int):
        name = f"TargetAssistant_{user_id}"
        try:
            return self.gc.open(name)
        except gspread.SpreadsheetNotFound:
            sh = self.gc.create(name)
            # Сделать листы
            sh.add_worksheet(title=GOAL_INFO_SHEET, rows=10, cols=3)
            sh.add_worksheet(title=PLAN_SHEET, rows=400, cols=4)
            # Удалить автосозданный пустой лист
            try:
                sh.del_worksheet(sh.sheet1)
            except Exception:
                pass
            # Делимся таблицей — любой, у кого есть ссылка, может редактировать
            try:
                sh.share('', perm_type="anyone", role="writer", with_link=True)
            except Exception as e:
                logger.warning("Не удалось установить публичный доступ к таблице: %s", e)
            return sh

    # -------------------------------------------------
    # Публичные методы
    # -------------------------------------------------
    def create_spreadsheet(self, user_id: int):
        sh = self._get_spreadsheet(user_id)
        # удостоверимся, что доступ открыт даже если таблица существовала
        try:
            sh.share('', perm_type="anyone", role="writer", with_link=True)
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
        return sh.url

    @RETRY
    def save_plan(self, user_id: int, plan: List[dict[str, Any]]):
        sh = self._get_spreadsheet(user_id)
        ws = sh.worksheet(PLAN_SHEET)
        header = [["Date", "DayOfWeek", "Task", "Status"]]
        rows = [[p["Date"], p["DayOfWeek"], p["Task"], p["Status"]] for p in plan]
        ws.update("A1", header + rows)

    @RETRY
    def get_goal_info(self, user_id: int):
        sh = self._get_spreadsheet(user_id)
        ws = sh.worksheet(GOAL_INFO_SHEET)
        data = ws.get_all_values()
        return {row[0]: row[1] for row in data if row}

    @RETRY
    def get_task_for_date(self, user_id: int, target_date: str):
        sh = self._get_spreadsheet(user_id)
        ws = sh.worksheet(PLAN_SHEET)
        data = ws.get_all_records()
        for row in data:
            if row.get("Date") == target_date:
                return row
        return None

    @RETRY
    def update_task_status(self, user_id: int, target_date: str, status: str):
        sh = self._get_spreadsheet(user_id)
        ws = sh.worksheet(PLAN_SHEET)
        data = ws.get_all_records()
        for idx, row in enumerate(data, start=2):  # включая заголовок в первой строке
            if row.get("Date") == target_date:
                ws.update_cell(idx, 4, status)  # 4-й столбец Status
                break

    @RETRY
    def get_statistics(self, user_id: int):
        sh = self._get_spreadsheet(user_id)
        ws = sh.worksheet(PLAN_SHEET)
        data = ws.get_all_records()
        total = len(data)
        done = sum(1 for r in data if r["Status"] == "Выполнено")
        percent = int(done / total * 100) if total else 0
        remaining = total - done
        return f"Выполнено {done} из {total} ({percent}%), осталось {remaining} дней"

    # -------------------------------------------------
    # Удаление таблицы целиком (для команды /reset)
    # -------------------------------------------------
    @RETRY
    def delete_spreadsheet(self, user_id: int):
        name = f"TargetAssistant_{user_id}"
        try:
            sh = self.gc.open(name)
            self.gc.del_spreadsheet(sh.id)
        except gspread.SpreadsheetNotFound:
            return 