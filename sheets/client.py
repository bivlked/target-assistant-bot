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
            # Таблица уже существует; далее убедимся, что листы переименованы и созданы при необходимости
            # Делимся таблицей — любой, у кого есть ссылка, может редактировать (на случай, если доступ не выставлен)
            try:
                sh.share("", perm_type="anyone", role="writer", with_link=True)
            except Exception:
                pass

            # --- Если таблица уже существует, убеждаемся, что листы имеют актуальные названия ----
            try:
                # Карта возможных старых названий → новые
                rename_map = {
                    "Цель": GOAL_INFO_SHEET,
                    "GoalInfo": GOAL_INFO_SHEET,
                    "Plan": PLAN_SHEET,
                }

                for old_title, new_title in rename_map.items():
                    try:
                        ws_old = sh.worksheet(old_title)
                        if ws_old.title != new_title:
                            ws_old.update_title(new_title)
                    except gspread.WorksheetNotFound:
                        # Старого листа нет – ок, создаём если нужно ниже
                        pass

                # Убеждаемся, что требуемые листы существуют
                try:
                    sh.worksheet(GOAL_INFO_SHEET)
                except gspread.WorksheetNotFound:
                    ws_new = sh.add_worksheet(title=GOAL_INFO_SHEET, rows=10, cols=3)
                    if hasattr(ws_new, "columns_auto_resize"):
                        try:
                            ws_new.columns_auto_resize(1, 1)
                        except Exception:
                            pass

                try:
                    sh.worksheet(PLAN_SHEET)
                except gspread.WorksheetNotFound:
                    sh.add_worksheet(title=PLAN_SHEET, rows=400, cols=4)
            except Exception as e:
                logger.warning("Ошибка проверки/переименования листов: %s", e)

            return sh
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
                sh.share("", perm_type="anyone", role="writer", with_link=True)
            except Exception as e:
                logger.warning(
                    "Не удалось установить публичный доступ к таблице: %s", e
                )
            return sh

    # -------------------------------------------------
    # Публичные методы
    # -------------------------------------------------
    def create_spreadsheet(self, user_id: int):
        sh = self._get_spreadsheet(user_id)
        # удостоверимся, что доступ открыт даже если таблица существовала
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
                ws = sh.add_worksheet(
                    title=title, rows=10, cols=3 if title == GOAL_INFO_SHEET else 4
                )
            ws.clear()

    @RETRY
    def save_goal_info(self, user_id: int, goal_data: dict[str, str]) -> str:
        sh = self._get_spreadsheet(user_id)
        ws = sh.worksheet(GOAL_INFO_SHEET)
        rows = [[k, v, ""] for k, v in goal_data.items()]
        ws.update("A1", rows)
        # форматирование
        try:
            ws.format("A:A", {"textFormat": {"bold": True}})
            if hasattr(ws, "columns_auto_resize"):
                # Автоширина всех трёх колонок (A:C)
                ws.columns_auto_resize(1, 3)
        except Exception:
            pass
        return sh.url

    @RETRY
    def save_plan(self, user_id: int, plan: List[dict[str, Any]]):
        sh = self._get_spreadsheet(user_id)
        ws = sh.worksheet(PLAN_SHEET)

        header = [list(PLAN_HEADERS)]
        rows = [
            [p[COL_DATE], p[COL_DAYOFWEEK], p[COL_TASK], p[COL_STATUS]] for p in plan
        ]
        ws.update("A1", header + rows)

        # --- Красивое форматирование ---------------------
        # 1. Сделать шапку жирной и по центру
        try:
            ws.format(
                "A1:D1",
                {
                    "textFormat": {"bold": True},
                    "horizontalAlignment": "CENTER",
                    # Светло-оранжевая заливка (RGB 255,229,204)
                    "backgroundColor": {"red": 1, "green": 0.898, "blue": 0.8},
                },
            )
            # 1.1 Центрируем весь столбец Дата (A)
            ws.format("A:A", {"horizontalAlignment": "CENTER"})
        except Exception:
            # Не критично, если форматирование не поддерживается
            pass

        # 2. Авто-ширина столбцов (если API доступен)
        if hasattr(ws, "columns_auto_resize"):
            try:
                ws.columns_auto_resize(1, 4)
            except Exception:
                pass

        # 3. Закрепляем (замораживаем) первую строку с заголовками, чтобы она всегда была видна
        try:
            if hasattr(ws, "freeze"):
                ws.freeze(rows=1)
        except Exception:
            # Игнорируем, если метод freeze недоступен или вызвал ошибку
            pass

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
            if row.get(COL_DATE) == target_date:
                return row
        return None

    @RETRY
    def update_task_status(self, user_id: int, target_date: str, status: str):
        sh = self._get_spreadsheet(user_id)
        ws = sh.worksheet(PLAN_SHEET)
        data = ws.get_all_records()
        for idx, row in enumerate(data, start=2):  # включая заголовок в первой строке
            if row.get(COL_DATE) == target_date:
                ws.update_cell(idx, 4, status)  # 4-й столбец Status
                break

    @RETRY
    def get_statistics(self, user_id: int):
        sh = self._get_spreadsheet(user_id)
        ws = sh.worksheet(PLAN_SHEET)
        data = ws.get_all_records()
        total = len(data)
        done = sum(1 for r in data if r[COL_STATUS] == "Выполнено")
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

    # -------------------------------------------------
    # Дополнительные методы для расширенной статистики
    # -------------------------------------------------

    @RETRY
    def get_spreadsheet_url(self, user_id: int) -> str:
        """Возвращает URL таблицы пользователя (создает при необходимости)."""
        return self._get_spreadsheet(user_id).url

    @RETRY
    def get_extended_statistics(self, user_id: int, upcoming_count: int = 5):
        """Возвращает подробную статистику и ближайшие задачи."""
        sh = self._get_spreadsheet(user_id)
        ws_plan = sh.worksheet(PLAN_SHEET)

        # Все строки (словари) без заголовка
        plan_rows = ws_plan.get_all_records()

        total_days = len(plan_rows)
        completed_days = sum(1 for r in plan_rows if r.get(COL_STATUS) == "Выполнено")
        progress_percent = int(completed_days / total_days * 100) if total_days else 0

        # --- Работа с датами в формате dd.mm.yyyy -------------------------
        # Импортируем здесь, чтобы избежать циклических зависимостей
        from datetime import datetime
        from utils.helpers import format_date  # локальный импорт

        def _parse(date_str: str):
            try:
                return datetime.strptime(date_str, "%d.%m.%Y")
            except ValueError:
                try:
                    return datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    return None

        today_dt = datetime.strptime(format_date(datetime.now()), "%d.%m.%Y")

        days_passed = sum(
            1
            for r in plan_rows
            if _parse(r.get(COL_DATE)) and _parse(r.get(COL_DATE)) < today_dt
        )
        days_left = total_days - days_passed

        # Ближайшие задачи, которые еще не выполнены и дата >= сегодня
        upcoming = [
            r
            for r in plan_rows
            if _parse(r.get(COL_DATE)) and _parse(r.get(COL_DATE)) >= today_dt
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
    @RETRY
    def _format_goal_sheet(self, user_id: int):
        """Применяет жирный стиль к A:A и авторазмер колонок на листе 'Информация о цели'."""
        try:
            sh = self._get_spreadsheet(user_id)
            ws = sh.worksheet(GOAL_INFO_SHEET)
            ws.format("A:A", {"textFormat": {"bold": True}})
            if hasattr(ws, "columns_auto_resize"):
                ws.columns_auto_resize(1, 3)
        except Exception:
            pass

    @RETRY
    def batch_update_task_statuses(self, user_id: int, updates: dict[str, str]):
        """Обновляет статусы нескольких дат одной операцией.

        updates: {"01.05.2025": "Выполнено", ...}
        При небольшом количестве дат используем последовательные update_cell;
        при необходимости можно оптимизировать batchUpdate запросом.
        """
        sh = self._get_spreadsheet(user_id)
        ws = sh.worksheet(PLAN_SHEET)
        data = ws.get_all_records()

        # Карта дата→row_index для быстрого доступа (строки начинаются с 2)
        row_map: dict[str, int] = {}
        for idx, row in enumerate(data, start=2):
            dt = row.get(COL_DATE)
            if dt:
                row_map[dt] = idx

        reqs: list[tuple[int, str]] = []
        for date_str, status in updates.items():
            row_idx = row_map.get(date_str)
            if row_idx:
                reqs.append((row_idx, status))
        # Пакетно — но простым циклом, gspread не имеет native batch_update_cell значений
        for row_idx, status in reqs:
            ws.update_cell(row_idx, 4, status)  # 4-й столбец Status
