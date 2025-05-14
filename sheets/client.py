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
from utils.cache import sheet_cache

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
    """Синхронный клиент Google Sheets.

    Экономит усилия на работе напрямую с API *gspread* и инкапсулирует всю
    доменно-специфичную логику (создание/получение таблиц, чтение и запись
    данных, форматирование листов, вычисление статистики). Методы
    декорированы ретраем Tenacity для устойчивой работы с нестабильной
    сетью/квотами Google.
    """

    def __init__(self):
        """Авторизуется в Google API и инициализирует объект `gspread`.

        Данные сервисного аккаунта берутся из ``config.google.credentials_path``.
        Поддерживаются скopes как для Google Sheets, так и для Google Drive –
        это позволяет открывать общий доступ к таблице через метод
        :py:meth:`gspread.Spreadsheet.share`.
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
        """Создаёт (или открывает) таблицу пользователя и открывает к ней доступ.*"""  # noqa: D401,E501
        sh = self._get_spreadsheet(user_id)
        try:
            sh.share("", perm_type="anyone", role="writer", with_link=True)
        except Exception:
            pass

        # invalidate cache
        sheet_cache.invalidate(user_id)

    @RETRY
    def clear_user_data(self, user_id: int):
        """Очищает оба листа пользователя, сохраняя структуру таблицы."""
        sh = self._get_spreadsheet(user_id)
        for title in (GOAL_INFO_SHEET, PLAN_SHEET):
            try:
                ws = sh.worksheet(title)
            except gspread.WorksheetNotFound:
                ws = sh.add_worksheet(
                    title=title, rows=10, cols=3 if title == GOAL_INFO_SHEET else 4
                )
            ws.clear()

        # invalidate cache
        sheet_cache.invalidate(user_id)

    @RETRY
    def save_goal_info(self, user_id: int, goal_data: dict[str, str]) -> str:
        """Записывает блок «Информация о цели» и возвращает URL таблицы."""
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

        # invalidate cache
        sheet_cache.invalidate(user_id)

        return sh.url

    @RETRY
    @sheet_cache.cached(lambda: "goal_info")
    def get_goal_info(self, user_id: int):
        """Возвращает словарь с параметрами цели (лист *Информация о цели*)."""
        ws = self._get_spreadsheet(user_id).worksheet(GOAL_INFO_SHEET)
        data = ws.get_all_values()
        return {row[0]: row[1] for row in data if row}

    @RETRY
    @sheet_cache.cached(lambda target_date: target_date)
    def get_task_for_date(self, user_id: int, target_date: str):
        """Ищет задачу на указанную дату в листе *План*.

        Возвращает dict строки таблицы или *None*, если задача не найдена.
        """
        ws = self._get_spreadsheet(user_id).worksheet(PLAN_SHEET)
        for row in ws.get_all_records():
            if row.get(COL_DATE) == target_date:
                return row
        return None

    @RETRY
    def update_task_status(self, user_id: int, target_date: str, status: str):
        """Обновляет поле *Статус* задачи в указанную дату."""
        ws = self._get_spreadsheet(user_id).worksheet(PLAN_SHEET)
        data = ws.get_all_records()
        for idx, row in enumerate(data, start=2):
            if row.get(COL_DATE) == target_date:
                ws.update_cell(idx, 4, status)
                break

        # invalidate cache
        sheet_cache.invalidate(user_id)

    @RETRY
    @sheet_cache.cached(lambda: "statistics")
    def get_statistics(self, user_id: int):
        """Краткая строковая статистика выполнения плана."""
        ws = self._get_spreadsheet(user_id).worksheet(PLAN_SHEET)
        data = ws.get_all_records()
        total = len(data)
        done = sum(1 for r in data if r[COL_STATUS] == "Выполнено")
        percent = int(done / total * 100) if total else 0
        remaining = total - done
        return f"Выполнено {done} из {total} ({percent}%), осталось {remaining} дней"

    @RETRY
    def delete_spreadsheet(self, user_id: int):
        """Навсегда удаляет таблицу пользователя из Google Drive."""
        name = f"TargetAssistant_{user_id}"
        try:
            sh = self.gc.open(name)
            self.gc.del_spreadsheet(sh.id)
        except gspread.SpreadsheetNotFound:
            return
        finally:
            # invalidate cache
            sheet_cache.invalidate(user_id)

    # --- batch update statuses ---
    @RETRY
    def batch_update_task_statuses(self, user_id: int, updates: dict[str, str]):
        """Пакетно обновляет статусы задач в несколько дат одной операцией."""
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
        sheet_cache.invalidate(user_id)

    # --- Дополнительные методы статистики и форматирования ------------------
    @RETRY
    @sheet_cache.cached(lambda: "spreadsheet_url")
    def get_spreadsheet_url(self, user_id: int) -> str:
        """Возвращает URL таблицы (создаёт её при необходимости)."""
        return self._get_spreadsheet(user_id).url

    @RETRY
    @sheet_cache.cached(lambda upcoming_count: f"extended_stats:{upcoming_count}")
    def get_extended_statistics(self, user_id: int, upcoming_count: int = 5):
        """Расширенная статистика + список ближайших задач.

        Параметры
        ----------
        user_id: int
            Telegram-ID пользователя.
        upcoming_count: int, default = 5
            Сколько ближайших (по дате) задач вернуть в списке
            ``upcoming_tasks``.
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
    @RETRY
    def _format_goal_sheet(self, user_id: int):
        """Жирный шрифт и авторазмер колонок на листе Информация о цели."""
        try:
            sh = self._get_spreadsheet(user_id)
            ws = sh.worksheet(GOAL_INFO_SHEET)
            ws.format("A:A", {"textFormat": {"bold": True}})
            if hasattr(ws, "columns_auto_resize"):
                ws.columns_auto_resize(1, 3)
        except Exception:
            pass

    # invalidate cache
    def invalidate_cache(self, user_id: int):
        sheet_cache.invalidate(user_id)
