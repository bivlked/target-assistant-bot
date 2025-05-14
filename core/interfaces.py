from __future__ import annotations

"""Common interfaces (Protocols) for dependency injection.
These allow GoalManager to depend on abstractions rather than concrete
Google-Sheets or OpenAI implementations.
"""

from typing import Protocol, Any, Dict, List


class StorageInterface(Protocol):
    """Abstract storage for user goals and daily tasks."""

    # Spreadsheet lifecycle
    def create_spreadsheet(self, user_id: int) -> None: ...

    def delete_spreadsheet(self, user_id: int) -> None: ...

    # Goal lifecycle
    def clear_user_data(self, user_id: int) -> None: ...

    def save_goal_info(self, user_id: int, info: Dict[str, Any]) -> str: ...

    def save_plan(self, user_id: int, plan: List[Dict[str, Any]]) -> None: ...

    # Daily workflow
    def get_task_for_date(self, user_id: int, date: str) -> Dict[str, Any] | None: ...

    def update_task_status(self, user_id: int, date: str, status: str) -> None: ...

    def batch_update_task_statuses(
        self, user_id: int, updates: Dict[str, str]
    ) -> None: ...

    # Statistics
    def get_statistics(self, user_id: int) -> str: ...

    def get_extended_statistics(self, user_id: int) -> Dict[str, Any]: ...

    def get_goal_info(self, user_id: int) -> Dict[str, Any]: ...


class LLMInterface(Protocol):
    """Abstract language-model client."""

    def generate_plan(
        self, goal_text: str, deadline: str, time: str
    ) -> List[Dict[str, Any]]: ...

    def generate_motivation(self, goal_text: str, progress_summary: str) -> str: ...


class AsyncStorageInterface(Protocol):
    """Abstract ASYNCHRONOUS storage for user goals and daily tasks."""

    # Spreadsheet lifecycle
    async def create_spreadsheet(self, user_id: int) -> None: ...
    async def delete_spreadsheet(self, user_id: int) -> None: ...

    # Goal lifecycle
    async def clear_user_data(self, user_id: int) -> None: ...
    async def save_goal_info(self, user_id: int, info: Dict[str, Any]) -> str: ...
    async def save_plan(self, user_id: int, plan: List[Dict[str, Any]]) -> None: ...

    # Daily workflow
    async def get_task_for_date(
        self, user_id: int, date: str
    ) -> Dict[str, Any] | None: ...
    async def update_task_status(
        self, user_id: int, date: str, status: str
    ) -> None: ...
    async def batch_update_task_statuses(
        self, user_id: int, updates: Dict[str, str]
    ) -> None: ...

    # Statistics
    async def get_statistics(self, user_id: int) -> str: ...
    async def get_extended_statistics(self, user_id: int) -> Dict[str, Any]: ...
    async def get_goal_info(self, user_id: int) -> Dict[str, Any]: ...


class AsyncLLMInterface(Protocol):
    """Abstract ASYNCHRONOUS language-model client."""

    async def generate_plan(
        self, goal_text: str, deadline: str, time: str
    ) -> List[Dict[str, Any]]: ...

    async def generate_motivation(
        self, goal_text: str, progress_summary: str
    ) -> str: ...
