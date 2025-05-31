#!/usr/bin/env python3
"""Synchronous Google Sheets client module using gspread with multi-goal support."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import gspread
import structlog
from google.oauth2.service_account import Credentials
from gspread import Client, Spreadsheet, Worksheet
from gspread.exceptions import APIError
from prometheus_client import Counter, Histogram
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import GoogleConfig, google
from core.metrics import SHEETS_API_CALLS, SHEETS_API_LATENCY
from core.models import Goal, GoalPriority, GoalStatistics, GoalStatus, Task, TaskStatus
from utils.cache import cached_sheet_method, invalidate_sheet_cache
from utils.helpers import (
    format_date,
    get_day_of_week,
)
from utils.retry_decorators import retry_google_sheets

# Constants for status values
USER_FACING_STATUS_DONE = "Выполнено"
USER_FACING_STATUS_NOT_DONE = "Не выполнено"

logger = structlog.get_logger()

# Prometheus metrics
sheets_api_calls = Counter("sheets_api_calls_total", "Total Google Sheets API calls")
sheets_api_latency = Histogram(
    "sheets_api_latency_seconds", "Google Sheets API call latency"
)
sheets_api_errors = Counter("sheets_api_errors_total", "Total Google Sheets API errors")

# Constants for sheet names and columns
GOAL_INFO_SHEET = "Информация о цели"  # Legacy single goal sheet
PLAN_SHEET = "План"  # Legacy single goal sheet

# New constants for multi-goal support
GOALS_LIST_SHEET = "Список целей"
GOAL_SHEET_PREFIX = "Цель "

# Headers for new multi-goal sheets
GOALS_LIST_HEADERS = [
    "ID цели",
    "Название цели",
    "Глобальная цель",
    "Срок выполнения",
    "Затраты в день",
    "Начало выполнения",
    "Статус",
    "Приоритет",
    "Теги",
    "Прогресс (%)",
    "Дата завершения",
]

# Constants for goal management
MAX_GOALS = 10

# Headers for plan sheets
PLAN_HEADERS = {
    "Дата": "Дата",
    "День недели": "День недели",
    "Задача": "Задача",
    "Статус": "Статус",
}

# Column names for compatibility
COL_DATE = PLAN_HEADERS["Дата"]
COL_DAYOFWEEK = PLAN_HEADERS["День недели"]
COL_TASK = PLAN_HEADERS["Задача"]
COL_STATUS = PLAN_HEADERS["Статус"]

# Google Sheets cell limit
GOOGLE_SHEETS_CELL_LIMIT = 5_000_000

# Retry decorator for legacy compatibility
RETRY = retry(
    retry=retry_if_exception_type(APIError),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
)


class SheetsManager:
    """Synchronous client for interacting with Google Sheets with multi-goal support.

    This class encapsulates all domain-specific logic for managing user spreadsheets,
    including creating/opening sheets, reading/writing goal and plan data,
    formatting cells, and calculating statistics. It supports both legacy single-goal
    mode and new multi-goal functionality.

    Implements the `StorageInterface` protocol.
    """

    def __init__(self):
        """Initializes the gspread client and authenticates with Google API."""
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(
            google.credentials_path, scopes=scopes
        )
        self.gc = gspread.authorize(creds)

    # -------------------------------------------------
    # Private helper methods
    # -------------------------------------------------
    def _get_spreadsheet(self, user_id: int) -> Spreadsheet:
        """Gets or creates a user's spreadsheet."""
        name = f"TargetAssistant_{user_id}"
        try:
            sh = self.gc.open(name)
            self._ensure_spreadsheet_structure(sh)
            return sh
        except gspread.SpreadsheetNotFound:
            sh = self.gc.create(name)
            self._initialize_spreadsheet(sh)
            return sh

    def _ensure_spreadsheet_structure(self, sh: Spreadsheet) -> None:
        """Ensures the spreadsheet has the correct structure for multi-goal support."""
        try:
            # Share with anyone
            sh.share("", perm_type="anyone", role="writer", with_link=True)
        except Exception:
            pass

        # Ensure Goals List sheet exists
        self._ensure_goals_list_sheet(sh)

        # Migrate legacy sheets if they exist
        self._migrate_legacy_sheets_if_needed(sh)

    def _initialize_spreadsheet(self, sh: Spreadsheet) -> None:
        """Initializes a new spreadsheet with multi-goal structure."""
        # Create Goals List sheet
        goals_ws = sh.add_worksheet(
            title=GOALS_LIST_SHEET, rows=15, cols=len(GOALS_LIST_HEADERS)
        )
        goals_ws.update(values=[GOALS_LIST_HEADERS], range_name="A1")
        self._format_goals_list_sheet(goals_ws)

        # Delete default Sheet1
        try:
            sh.del_worksheet(sh.sheet1)
        except Exception:
            pass

        # Share with anyone
        try:
            sh.share("", perm_type="anyone", role="writer", with_link=True)
        except Exception as e:
            logger.warning("Failed to share spreadsheet: %s", e)

    def _ensure_goals_list_sheet(self, sh: Spreadsheet) -> None:
        """Ensures the Goals List sheet exists and is properly formatted."""
        try:
            ws = sh.worksheet(GOALS_LIST_SHEET)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(
                title=GOALS_LIST_SHEET, rows=15, cols=len(GOALS_LIST_HEADERS)
            )
            ws.update(values=[GOALS_LIST_HEADERS], range_name="A1")
            self._format_goals_list_sheet(ws)

    def _format_goals_list_sheet(self, ws: Worksheet) -> None:
        """Formats the Goals List sheet."""
        try:
            ws.format(
                "A1:K1",
                {
                    "textFormat": {"bold": True},
                    "horizontalAlignment": "CENTER",
                    "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 1},
                },
            )
            if hasattr(ws, "freeze"):
                ws.freeze(rows=1)
            if hasattr(ws, "columns_auto_resize"):
                ws.columns_auto_resize(1, len(GOALS_LIST_HEADERS))
        except Exception as e:
            logger.warning("Failed to format goals list sheet: %s", e)

    def _ensure_goal_sheet(self, sh: Spreadsheet, goal_id: int) -> None:
        """Ensures a sheet for a specific goal exists."""
        sheet_name = f"{GOAL_SHEET_PREFIX}{goal_id}"
        try:
            ws = sh.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=sheet_name, rows=400, cols=4)
            ws.update(values=[list(PLAN_HEADERS.values())], range_name="A1")
            self._format_plan_sheet(ws)

    def _format_plan_sheet(self, ws: Worksheet) -> None:
        """Formats a plan sheet."""
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
            if hasattr(ws, "freeze"):
                ws.freeze(rows=1)
            if hasattr(ws, "columns_auto_resize"):
                ws.columns_auto_resize(1, 4)
        except Exception as e:
            logger.warning("Failed to format plan sheet: %s", e)

    def _migrate_legacy_sheets_if_needed(self, sh: Spreadsheet) -> None:
        """Migrates legacy single-goal sheets to multi-goal structure if they exist."""
        try:
            # Check if legacy sheets exist
            goal_info_exists = False
            plan_exists = False

            try:
                goal_info_ws = sh.worksheet(GOAL_INFO_SHEET)
                goal_info_exists = True
            except gspread.WorksheetNotFound:
                pass

            try:
                plan_ws = sh.worksheet(PLAN_SHEET)
                plan_exists = True
            except gspread.WorksheetNotFound:
                pass

            # If both legacy sheets exist, migrate to goal 1
            if goal_info_exists and plan_exists:
                logger.info("Migrating legacy sheets for user")

                # Get goal info
                goal_data = {}
                if goal_info_exists:
                    data = goal_info_ws.get_all_values()
                    goal_data = {
                        row[0]: row[1] for row in data if row and len(row) >= 2
                    }

                # Get plan data
                plan_data = []
                if plan_exists:
                    plan_data = plan_ws.get_all_records()

                if goal_data:
                    # Calculate progress
                    total_tasks = len(plan_data)
                    completed_tasks = sum(
                        1
                        for t in plan_data
                        if t.get(COL_STATUS) == USER_FACING_STATUS_DONE
                    )
                    progress = (
                        int(completed_tasks / total_tasks * 100) if total_tasks else 0
                    )

                    # Add to Goals List
                    goals_ws = sh.worksheet(GOALS_LIST_SHEET)
                    goal_row = [
                        "1",  # ID
                        "Цель 1",  # Default name
                        goal_data.get("Глобальная цель", ""),
                        goal_data.get("Срок выполнения", ""),
                        goal_data.get("Затраты в день", ""),
                        goal_data.get("Начало выполнения", ""),
                        GoalStatus.ACTIVE.value,
                        GoalPriority.MEDIUM.value,
                        "",  # No tags
                        str(progress),
                        "",  # No completion date
                    ]
                    goals_ws.append_row(goal_row)

                    # Rename Plan sheet to "Цель 1"
                    if plan_exists:
                        plan_ws.update_title(f"{GOAL_SHEET_PREFIX}1")

        except Exception as e:
            logger.error("Error during migration", exc_info=e)

    # -------------------------------------------------
    # Multi-goal management methods
    # -------------------------------------------------
    @retry_google_sheets
    def get_all_goals(self, user_id: int) -> List[Goal]:
        """Get all goals for a user."""
        sh = self._get_spreadsheet(user_id)
        goals_ws = sh.worksheet(GOALS_LIST_SHEET)

        goals = []
        for row in goals_ws.get_all_records():
            if row.get("ID цели"):
                try:
                    goals.append(Goal.from_sheet_row(row))
                except Exception as e:
                    logger.error("Error parsing goal row", exc_info=e)

        return goals

    @retry_google_sheets
    def get_goal_by_id(self, user_id: int, goal_id: int) -> Optional[Goal]:
        """Get a specific goal by ID."""
        goals = self.get_all_goals(user_id)
        for goal in goals:
            if goal.goal_id == goal_id:
                return goal
        return None

    @retry_google_sheets
    def get_active_goals(self, user_id: int) -> List[Goal]:
        """Get only active goals."""
        goals = self.get_all_goals(user_id)
        return [g for g in goals if g.status == GoalStatus.ACTIVE]

    @retry_google_sheets
    def get_active_goals_count(self, user_id: int) -> int:
        """Count active goals."""
        return len(self.get_active_goals(user_id))

    @retry_google_sheets
    def get_next_goal_id(self, user_id: int) -> int:
        """Get next available goal ID."""
        goals = self.get_all_goals(user_id)
        used_ids = {g.goal_id for g in goals}

        for i in range(1, MAX_GOALS + 1):
            if i not in used_ids:
                return i

        raise ValueError(f"Goal limit reached ({MAX_GOALS})")

    @retry_google_sheets
    def save_goal_info(self, user_id: int, goal: Goal) -> str:
        """Save or update goal information."""
        sh = self._get_spreadsheet(user_id)
        goals_ws = sh.worksheet(GOALS_LIST_SHEET)

        # Find existing row
        existing_row = None
        all_values = goals_ws.get_all_values()
        for idx, row in enumerate(all_values[1:], start=2):  # Skip header
            if row and row[0] == str(goal.goal_id):
                existing_row = idx
                break

        # Update or add
        row_data = goal.to_sheet_row()
        if existing_row:
            goals_ws.update(values=[row_data], range_name=f"A{existing_row}")
        else:
            goals_ws.append_row(row_data)

        # Ensure goal sheet exists
        self._ensure_goal_sheet(sh, goal.goal_id)

        invalidate_sheet_cache(user_id)
        return sh.url

    @retry_google_sheets
    def update_goal_status(
        self, user_id: int, goal_id: int, status: GoalStatus
    ) -> None:
        """Update goal status."""
        goal = self.get_goal_by_id(user_id, goal_id)
        if goal:
            goal.status = status
            if status == GoalStatus.COMPLETED and not goal.completion_date:
                goal.completion_date = format_date(datetime.now(timezone.utc))
            self.save_goal_info(user_id, goal)

    @retry_google_sheets
    def update_goal_progress(self, user_id: int, goal_id: int, progress: int) -> None:
        """Update goal progress percentage."""
        sh = self._get_spreadsheet(user_id)

        # Calculate progress from tasks
        sheet_name = f"{GOAL_SHEET_PREFIX}{goal_id}"
        try:
            ws = sh.worksheet(sheet_name)
            tasks = ws.get_all_records()

            total = len(tasks)
            done = sum(1 for t in tasks if t.get(COL_STATUS) == USER_FACING_STATUS_DONE)
            calculated_progress = int(done / total * 100) if total else 0

            # Update in Goals List
            goals_ws = sh.worksheet(GOALS_LIST_SHEET)
            all_values = goals_ws.get_all_values()

            for idx, row in enumerate(all_values[1:], start=2):
                if row and row[0] == str(goal_id):
                    goals_ws.update_cell(
                        idx, 10, str(calculated_progress)
                    )  # Progress column

                    # If 100%, update status
                    if calculated_progress == 100:
                        goals_ws.update_cell(idx, 7, GoalStatus.COMPLETED.value)
                        goals_ws.update_cell(
                            idx, 11, format_date(datetime.now(timezone.utc))
                        )
                    break

        except gspread.WorksheetNotFound:
            pass

        invalidate_sheet_cache(user_id)

    @retry_google_sheets
    def update_goal_priority(
        self, user_id: int, goal_id: int, priority: GoalPriority
    ) -> None:
        """Update goal priority."""
        goal = self.get_goal_by_id(user_id, goal_id)
        if goal:
            goal.priority = priority
            self.save_goal_info(user_id, goal)

    @retry_google_sheets
    def archive_goal(self, user_id: int, goal_id: int) -> None:
        """Archive a goal."""
        self.update_goal_status(user_id, goal_id, GoalStatus.ARCHIVED)

    @retry_google_sheets
    def delete_goal(self, user_id: int, goal_id: int) -> None:
        """Delete a goal completely."""
        sh = self._get_spreadsheet(user_id)

        # Remove from Goals List
        goals_ws = sh.worksheet(GOALS_LIST_SHEET)
        all_values = goals_ws.get_all_values()

        for idx, row in enumerate(all_values[1:], start=2):
            if row and row[0] == str(goal_id):
                goals_ws.delete_rows(idx)
                break

        # Delete goal sheet
        sheet_name = f"{GOAL_SHEET_PREFIX}{goal_id}"
        try:
            goal_ws = sh.worksheet(sheet_name)
            sh.del_worksheet(goal_ws)
        except gspread.WorksheetNotFound:
            pass

        invalidate_sheet_cache(user_id)

    @retry_google_sheets
    def save_plan(self, user_id: int, goal_id: int, plan: List[Dict[str, Any]]) -> None:
        """Save plan for a goal."""
        sh = self._get_spreadsheet(user_id)
        self._ensure_goal_sheet(sh, goal_id)

        sheet_name = f"{GOAL_SHEET_PREFIX}{goal_id}"
        ws = sh.worksheet(sheet_name)

        # Clear existing content
        ws.clear()

        # Write new plan
        header = [list(PLAN_HEADERS.values())]
        rows = [
            [p[COL_DATE], p[COL_DAYOFWEEK], p[COL_TASK], p[COL_STATUS]] for p in plan
        ]
        ws.update(values=header + rows, range_name="A1")

        # Format
        self._format_plan_sheet(ws)

        invalidate_sheet_cache(user_id)

    @retry_google_sheets
    def get_plan_for_goal(self, user_id: int, goal_id: int) -> List[Task]:
        """Get plan for a specific goal."""
        sh = self._get_spreadsheet(user_id)
        sheet_name = f"{GOAL_SHEET_PREFIX}{goal_id}"

        try:
            ws = sh.worksheet(sheet_name)
            tasks = []
            for row in ws.get_all_records():
                if row.get(COL_DATE):
                    task = Task.from_sheet_row(row, goal_id)
                    tasks.append(task)
            return tasks
        except gspread.WorksheetNotFound:
            return []

    @retry_google_sheets
    def get_task_for_date(
        self, user_id: int, goal_id: int, date: str
    ) -> Optional[Task]:
        """Get task for specific goal and date."""
        tasks = self.get_plan_for_goal(user_id, goal_id)
        for task in tasks:
            if task.date == date:
                return task
        return None

    @retry_google_sheets
    def get_all_tasks_for_date(self, user_id: int, date: str) -> List[Task]:
        """Get all tasks for a specific date."""
        tasks = []
        active_goals = self.get_active_goals(user_id)

        sh = self._get_spreadsheet(user_id)

        for goal in active_goals:
            sheet_name = f"{GOAL_SHEET_PREFIX}{goal.goal_id}"
            try:
                ws = sh.worksheet(sheet_name)
                for row in ws.get_all_records():
                    if row.get(COL_DATE) == date:
                        task = Task.from_sheet_row(row, goal.goal_id, goal.name)
                        tasks.append(task)
                        break
            except gspread.WorksheetNotFound:
                continue

        return tasks

    @retry_google_sheets
    def update_task_status(
        self, user_id: int, goal_id: int, date: str, status: str
    ) -> None:
        """Update task status."""
        sh = self._get_spreadsheet(user_id)
        sheet_name = f"{GOAL_SHEET_PREFIX}{goal_id}"

        try:
            ws = sh.worksheet(sheet_name)
            data = ws.get_all_records()

            for idx, row in enumerate(data, start=2):
                if row.get(COL_DATE) == date:
                    ws.update_cell(idx, 4, status)
                    break

            # Update goal progress
            self.update_goal_progress(
                user_id, goal_id, 0
            )  # Progress will be recalculated

        except gspread.WorksheetNotFound:
            pass

        invalidate_sheet_cache(user_id)

    @retry_google_sheets
    def batch_update_task_statuses(
        self, user_id: int, updates: Dict[Tuple[int, str], str]
    ) -> None:
        """Batch update multiple task statuses."""
        sh = self._get_spreadsheet(user_id)

        # Group updates by goal
        updates_by_goal: Dict[int, Dict[str, str]] = {}
        for (goal_id, date), status in updates.items():
            if goal_id not in updates_by_goal:
                updates_by_goal[goal_id] = {}
            updates_by_goal[goal_id][date] = status

        # Apply updates
        for goal_id, date_updates in updates_by_goal.items():
            sheet_name = f"{GOAL_SHEET_PREFIX}{goal_id}"
            try:
                ws = sh.worksheet(sheet_name)
                data = ws.get_all_records()

                batch_updates = []
                for idx, row in enumerate(data, start=2):
                    row_date = str(row.get(COL_DATE, ""))
                    if row_date and row_date in date_updates:
                        batch_updates.append(
                            {"range": f"D{idx}", "values": [[date_updates[row_date]]]}
                        )

                if batch_updates:
                    ws.batch_update(batch_updates)

                # Update goal progress
                self.update_goal_progress(user_id, goal_id, 0)

            except gspread.WorksheetNotFound:
                continue

        invalidate_sheet_cache(user_id)

    @retry_google_sheets
    def get_goal_statistics(self, user_id: int, goal_id: int) -> GoalStatistics:
        """Get statistics for a specific goal."""
        goal = self.get_goal_by_id(user_id, goal_id)
        if not goal:
            return GoalStatistics(0, 0, 0, 0, 0, 0.0)

        tasks = self.get_plan_for_goal(user_id, goal_id)
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.DONE)
        progress_percent = (
            int(completed_tasks / total_tasks * 100) if total_tasks else 0
        )

        # Calculate days
        today = datetime.now(timezone.utc)
        start_date = datetime.strptime(goal.start_date, "%d.%m.%Y").replace(
            tzinfo=timezone.utc
        )
        days_elapsed = (today - start_date).days

        # Estimate total days from tasks
        days_remaining = total_tasks - days_elapsed if total_tasks > days_elapsed else 0

        completion_rate = completed_tasks / days_elapsed if days_elapsed > 0 else 0.0

        return GoalStatistics(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            progress_percent=progress_percent,
            days_elapsed=days_elapsed,
            days_remaining=days_remaining,
            completion_rate=completion_rate,
        )

    @retry_google_sheets
    def get_overall_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get overall statistics for all goals."""
        goals = self.get_all_goals(user_id)
        active_goals = [g for g in goals if g.status == GoalStatus.ACTIVE]
        completed_goals = [g for g in goals if g.status == GoalStatus.COMPLETED]
        archived_goals = [g for g in goals if g.status == GoalStatus.ARCHIVED]

        total_progress = 0
        if active_goals:
            total_progress = sum(g.progress_percent for g in active_goals) // len(
                active_goals
            )

        return {
            "total_goals": len(goals),
            "active_count": len(active_goals),
            "completed_count": len(completed_goals),
            "archived_count": len(archived_goals),
            "total_progress": total_progress,
            "active_goals": active_goals,
            "can_add_more": len(active_goals) < MAX_GOALS,
        }

    # -------------------------------------------------
    # Legacy methods for backward compatibility
    # -------------------------------------------------
    def create_spreadsheet(self, user_id: int):
        """Creates (if not exists) or opens a user's spreadsheet."""
        self._get_spreadsheet(user_id)
        invalidate_sheet_cache(user_id)

    @retry_google_sheets
    def clear_user_data(self, user_id: int):
        """Clears all data - legacy method that now archives all goals."""
        goals = self.get_active_goals(user_id)
        for goal in goals:
            self.archive_goal(user_id, goal.goal_id)

    @retry_google_sheets
    def get_goal_info(self, user_id: int) -> Dict[str, str]:
        """Legacy method - returns info for first active goal."""
        goals = self.get_active_goals(user_id)
        if not goals:
            return {}

        goal = goals[0]
        return {
            "Глобальная цель": goal.description,
            "Срок выполнения": goal.deadline,
            "Затраты в день": goal.daily_time,
            "Начало выполнения": goal.start_date,
        }

    @retry_google_sheets
    def save_goal_and_plan(
        self, user_id: int, goal_data: Dict[str, str], plan: List[Dict[str, Any]]
    ) -> str:
        """Legacy method - creates goal as ID 1."""
        # Check if goal 1 exists
        existing_goal = self.get_goal_by_id(user_id, 1)
        if existing_goal:
            # Archive it first
            self.archive_goal(user_id, 1)

        # Create new goal
        goal = Goal(
            goal_id=1,
            name="Моя цель",
            description=goal_data.get("Глобальная цель", ""),
            deadline=goal_data.get("Срок выполнения", ""),
            daily_time=goal_data.get("Затраты в день", ""),
            start_date=goal_data.get("Начало выполнения", ""),
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.MEDIUM,
            tags=[],
            progress_percent=0,
        )

        url = self.save_goal_info(user_id, goal)
        self.save_plan(user_id, 1, plan)
        return url

    @retry_google_sheets
    def get_task_for_today(self, user_id: int) -> Dict[str, Any] | None:
        """Legacy method - returns first task for today."""
        today = format_date(datetime.now(timezone.utc))
        tasks = self.get_all_tasks_for_date(user_id, today)

        if tasks:
            task = tasks[0]
            return {
                COL_DATE: task.date,
                COL_DAYOFWEEK: task.day_of_week,
                COL_TASK: task.task,
                COL_STATUS: task.status.value,
            }
        return None

    @retry_google_sheets
    def update_task_status_old(self, user_id: int, date: str, status: str) -> None:
        """Legacy method - updates status for first goal's task."""
        goals = self.get_active_goals(user_id)
        if goals:
            self.update_task_status(user_id, goals[0].goal_id, date, status)

    @retry_google_sheets
    def get_status_message(self, user_id: int) -> str:
        """Legacy method - returns status for first goal."""
        goals = self.get_active_goals(user_id)
        if not goals:
            return "Нет активных целей"

        stats = self.get_goal_statistics(user_id, goals[0].goal_id)
        return (
            f"Выполнено {stats.completed_tasks} из {stats.total_tasks} "
            f"({stats.progress_percent}%), осталось {stats.days_remaining} дней"
        )

    @retry_google_sheets
    def delete_spreadsheet(self, user_id: int):
        """Permanently deletes the user's spreadsheet from Google Drive."""
        name = f"TargetAssistant_{user_id}"
        try:
            sh = self.gc.open(name)
            self.gc.del_spreadsheet(sh.id)
        except gspread.SpreadsheetNotFound:
            return
        finally:
            invalidate_sheet_cache(user_id)

    @retry_google_sheets
    def get_spreadsheet_url(self, user_id: int) -> str:
        """Returns the URL of the user's spreadsheet."""
        sh = self._get_spreadsheet(user_id)
        return sh.url

    @retry_google_sheets
    def get_extended_statistics(
        self, user_id: int, upcoming_count: int = 5
    ) -> Dict[str, Any]:
        """Legacy extended statistics - uses first active goal."""
        goals = self.get_active_goals(user_id)
        if not goals:
            return {
                "total_days": 0,
                "completed_days": 0,
                "progress_percent": 0,
                "days_passed": 0,
                "days_left": 0,
                "upcoming_tasks": [],
                "sheet_url": self.get_spreadsheet_url(user_id),
            }

        goal = goals[0]
        stats = self.get_goal_statistics(user_id, goal.goal_id)
        tasks = self.get_plan_for_goal(user_id, goal.goal_id)

        # Get upcoming tasks
        today = datetime.now(timezone.utc)
        upcoming = []
        for task in tasks:
            try:
                task_date = datetime.strptime(task.date, "%d.%m.%Y").replace(
                    tzinfo=timezone.utc
                )
                if task_date >= today and task.status != TaskStatus.DONE:
                    upcoming.append(
                        {
                            COL_DATE: task.date,
                            COL_DAYOFWEEK: task.day_of_week,
                            COL_TASK: task.task,
                            COL_STATUS: task.status.value,
                        }
                    )
            except ValueError:
                continue

        upcoming = upcoming[:upcoming_count]

        return {
            "total_days": stats.total_tasks,
            "completed_days": stats.completed_tasks,
            "progress_percent": stats.progress_percent,
            "days_passed": stats.days_elapsed,
            "days_left": stats.days_remaining,
            "upcoming_tasks": upcoming,
            "sheet_url": self.get_spreadsheet_url(user_id),
        }

    # Legacy compatibility
    get_statistics = get_status_message
    batch_update_task_statuses_legacy = batch_update_task_statuses
