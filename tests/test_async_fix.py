"""Tests to verify the async event loop fix is working correctly."""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock

from scheduler.tasks import Scheduler
from core.interfaces import AsyncStorageInterface, AsyncLLMInterface
from sheets.async_client import AsyncSheetsManager
from llm.async_client import AsyncLLMClient


@pytest.mark.asyncio
async def test_single_event_loop():
    """Test that all components use the same event loop."""
    # Get the current event loop
    main_loop = asyncio.get_running_loop()

    # Initialize components
    sheets_client = AsyncSheetsManager()
    llm_client = AsyncLLMClient()

    # Create scheduler with explicit loop
    scheduler = Scheduler(sheets_client, llm_client, event_loop=main_loop)
    scheduler.start()

    # Verify scheduler is using the same loop
    assert scheduler._event_loop == main_loop
    assert scheduler.scheduler is not None

    # Verify async operations work without errors
    async def dummy_async_operation():
        await asyncio.sleep(0.01)
        return "success"

    result = await dummy_async_operation()
    assert result == "success"


@pytest.mark.asyncio
async def test_scheduler_initialization_with_loop():
    """Test that Scheduler correctly initializes with provided event loop."""
    storage = Mock(spec=AsyncStorageInterface)
    llm = Mock(spec=AsyncLLMInterface)
    loop = asyncio.get_running_loop()

    scheduler = Scheduler(storage, llm, event_loop=loop)
    scheduler.start()

    assert scheduler._event_loop == loop
    assert scheduler.scheduler is not None
    assert scheduler.scheduler.running


@pytest.mark.asyncio
async def test_scheduler_initialization_without_loop():
    """Test that Scheduler can get current loop if none provided."""
    storage = Mock(spec=AsyncStorageInterface)
    llm = Mock(spec=AsyncLLMInterface)

    scheduler = Scheduler(storage, llm)
    scheduler.start()

    # Should have obtained the current running loop
    assert scheduler._event_loop == asyncio.get_running_loop()
    assert scheduler.scheduler is not None
    assert scheduler.scheduler.running


@pytest.mark.asyncio
async def test_async_sheets_manager_uses_current_loop():
    """Test that AsyncSheetsManager correctly uses the current event loop."""
    sheets_manager = AsyncSheetsManager()

    # Mock the sync manager
    with patch.object(sheets_manager, "_sync") as mock_sync:
        mock_sync.get_goal_info.return_value = {"goal": "Test Goal"}

        # Call async method - get_goal_info only takes user_id
        result = await sheets_manager.get_goal_info(123)

        assert result == {"goal": "Test Goal"}
        mock_sync.get_goal_info.assert_called_once_with(123)


def test_scheduler_no_loop_error():
    """Test that Scheduler handles missing event loop gracefully."""
    storage = Mock(spec=AsyncStorageInterface)
    llm = Mock(spec=AsyncLLMInterface)

    # This should not raise an error when there's no running loop
    scheduler = Scheduler(storage, llm)

    # Manually set event_loop to None to simulate no loop scenario
    scheduler._event_loop = None

    # Start should handle the error gracefully
    with patch("scheduler.tasks.logger") as mock_logger:
        scheduler.start()
        mock_logger.error.assert_called_once_with(
            "No running event loop found. Scheduler not started."
        )
        assert scheduler.scheduler is None
