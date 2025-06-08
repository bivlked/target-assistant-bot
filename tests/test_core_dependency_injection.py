"""Tests for core dependency injection container."""

import pytest
from unittest.mock import Mock

import core.dependency_injection as di_module
from core.dependency_injection import (
    initialize_dependencies,
    get_async_storage,
    get_async_llm,
)


def test_initialize_dependencies():
    """Tests that initialize_dependencies sets global instances correctly."""
    # Create mock instances
    mock_storage = Mock()
    mock_llm = Mock()

    # Initialize dependencies
    initialize_dependencies(mock_storage, mock_llm)

    # Verify instances are set
    assert get_async_storage() is mock_storage
    assert get_async_llm() is mock_llm


def test_get_async_storage_when_not_initialized():
    """Tests that get_async_storage raises RuntimeError when not initialized."""
    # Reset global state
    original_storage = di_module._storage_instance
    di_module._storage_instance = None

    try:
        with pytest.raises(RuntimeError) as exc_info:
            get_async_storage()

        assert "Storage not initialized" in str(exc_info.value)
        assert "Call initialize_dependencies() first" in str(exc_info.value)
    finally:
        # Restore original state
        di_module._storage_instance = original_storage


def test_get_async_llm_when_not_initialized():
    """Tests that get_async_llm raises RuntimeError when not initialized."""
    # Reset global state
    original_llm = di_module._llm_instance
    di_module._llm_instance = None

    try:
        with pytest.raises(RuntimeError) as exc_info:
            get_async_llm()

        assert "LLM not initialized" in str(exc_info.value)
        assert "Call initialize_dependencies() first" in str(exc_info.value)
    finally:
        # Restore original state
        di_module._llm_instance = original_llm


def test_dependency_injection_workflow():
    """Tests the complete workflow of dependency injection."""
    # Create mock instances
    mock_storage = Mock()
    mock_llm = Mock()

    # Initialize dependencies
    initialize_dependencies(mock_storage, mock_llm)

    # Get instances and verify they're the same objects
    storage = get_async_storage()
    llm = get_async_llm()

    assert storage is mock_storage
    assert llm is mock_llm

    # Verify we can call methods on the mocks
    storage.some_method = Mock(return_value="storage_result")
    llm.some_method = Mock(return_value="llm_result")

    assert storage.some_method() == "storage_result"
    assert llm.some_method() == "llm_result"


def test_reinitialize_dependencies():
    """Tests that dependencies can be reinitialized with new instances."""
    # Create first set of mocks
    mock_storage_1 = Mock()
    mock_llm_1 = Mock()

    initialize_dependencies(mock_storage_1, mock_llm_1)

    assert get_async_storage() is mock_storage_1
    assert get_async_llm() is mock_llm_1

    # Create second set of mocks
    mock_storage_2 = Mock()
    mock_llm_2 = Mock()

    initialize_dependencies(mock_storage_2, mock_llm_2)

    # Verify instances are updated
    assert get_async_storage() is mock_storage_2
    assert get_async_llm() is mock_llm_2
    assert get_async_storage() is not mock_storage_1
    assert get_async_llm() is not mock_llm_1
