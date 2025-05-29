"""Dependency injection container for Target Assistant Bot."""

from __future__ import annotations

from typing import Optional

# Global instances - simple DI container
_storage_instance: Optional[object] = None
_llm_instance: Optional[object] = None


def initialize_dependencies(storage, llm) -> None:
    """Initialize the dependency injection container.

    Args:
        storage: AsyncStorageInterface implementation
        llm: AsyncLLMInterface implementation
    """
    global _storage_instance, _llm_instance
    _storage_instance = storage
    _llm_instance = llm


def get_async_storage():
    """Get the storage instance.

    Returns:
        AsyncStorageInterface implementation

    Raises:
        RuntimeError: If dependencies are not initialized
    """
    if _storage_instance is None:
        raise RuntimeError(
            "Storage not initialized. Call initialize_dependencies() first."
        )
    return _storage_instance


def get_async_llm():
    """Get the LLM instance.

    Returns:
        AsyncLLMInterface implementation

    Raises:
        RuntimeError: If dependencies are not initialized
    """
    if _llm_instance is None:
        raise RuntimeError("LLM not initialized. Call initialize_dependencies() first.")
    return _llm_instance
