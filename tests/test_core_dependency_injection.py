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
    """Test dependency reinitialization"""
    from unittest.mock import Mock

    # Create mock instances
    mock_storage = Mock()
    mock_llm = Mock()

    # Initialize dependencies with mocks
    initialize_dependencies(mock_storage, mock_llm)

    # Get services
    storage = get_async_storage()
    llm = get_async_llm()

    assert storage is mock_storage
    assert llm is mock_llm

    # Create new mocks for reinitialization
    new_mock_storage = Mock()
    new_mock_llm = Mock()

    # Reinitialize
    initialize_dependencies(new_mock_storage, new_mock_llm)

    # Should get new instances
    new_storage = get_async_storage()
    new_llm = get_async_llm()

    assert new_storage is new_mock_storage
    assert new_llm is new_mock_llm
    assert new_storage is not mock_storage
    assert new_llm is not mock_llm


def test_performance_metrics():
    """Test DI container performance metrics"""
    from shared.container.dependency_container import DependencyContainer

    container = DependencyContainer()
    metrics = container.get_performance_metrics()

    # Initial state
    assert metrics.get_cache_hit_ratio() == 0.0
    assert metrics.get_average_resolution_time("test") == 0.0

    # Register a simple service to generate metrics
    class ITestService:
        pass

    class TestService(ITestService):
        def __init__(self):
            pass

    container.register_singleton(ITestService, TestService)

    # This should create metrics
    service = container.resolve(ITestService)

    # Check that metrics were recorded
    assert container._metrics.cache_hits > 0
    assert isinstance(service, TestService)


def test_batch_resolution():
    """Test batch resolution functionality"""
    from shared.container.dependency_container import DependencyContainer

    container = DependencyContainer()

    # Register some simple services for testing
    class IService1:
        pass

    class Service1(IService1):
        def __init__(self):
            pass

    class IService2:
        pass

    class Service2(IService2):
        def __init__(self):
            pass

    container.register_singleton(IService1, Service1)
    container.register_singleton(IService2, Service2)

    # Test batch resolution
    interfaces = [IService1, IService2]
    results = container.resolve_batch(interfaces)

    assert len(results) == 2
    assert IService1 in results
    assert IService2 in results
    assert isinstance(results[IService1], Service1)
    assert isinstance(results[IService2], Service2)


def test_service_key_caching():
    """Test service key caching optimization"""
    from shared.container.dependency_container import DependencyContainer

    container = DependencyContainer()

    class ITestService:
        pass

    # First call should populate cache
    key1 = container._get_key_optimized(ITestService)
    assert ITestService in container._service_keys_cache

    # Second call should use cache
    key2 = container._get_key_optimized(ITestService)
    assert key1 == key2

    # Cache should contain the mapping
    assert container._service_keys_cache[ITestService] == key1


def test_constructor_signature_caching():
    """Test constructor signature caching"""
    from shared.container.dependency_container import DependencyContainer

    container = DependencyContainer()

    class TestClass:
        def __init__(self, param1: str):
            self.param1 = param1

    # First call should populate cache
    sig1 = container._get_constructor_signature(TestClass)
    assert TestClass in container._constructor_cache

    # Second call should use cache
    sig2 = container._get_constructor_signature(TestClass)
    assert sig1 is sig2  # Should be the exact same object

    # Verify signature content
    params = list(sig1.parameters.keys())
    assert "self" in params
    assert "param1" in params


def test_cache_clearing():
    """Test cache clearing functionality"""
    from shared.container.dependency_container import DependencyContainer

    container = DependencyContainer()

    class ITestService:
        pass

    class TestService:
        def __init__(self):
            pass

    # Populate caches
    container._get_key_optimized(ITestService)
    container._get_constructor_signature(TestService)

    # Verify caches are populated
    assert len(container._service_keys_cache) > 0
    assert len(container._constructor_cache) > 0

    # Clear caches
    container.clear_caches()

    # Verify caches are cleared
    assert len(container._service_keys_cache) == 0
    assert len(container._constructor_cache) == 0
    assert len(container._dependency_graph) == 0


def test_dependency_graph_building():
    """Test dependency graph building for optimization"""
    from shared.container.dependency_container import DependencyContainer

    container = DependencyContainer()

    class IDependency:
        pass

    class Dependency(IDependency):
        pass

    class IService:
        pass

    class Service(IService):
        def __init__(self, dep: IDependency):
            self.dep = dep

    # Register services
    container.register_singleton(IDependency, Dependency)
    container.register_singleton(IService, Service)

    # Check dependency graph was built
    service_key = container._get_key_optimized(IService)
    dep_key = container._get_key_optimized(IDependency)

    assert service_key in container._dependency_graph
    assert dep_key in container._dependency_graph[service_key]


def test_performance_metrics_recording():
    """Test performance metrics recording"""
    from shared.container.dependency_container import PerformanceMetrics

    metrics = PerformanceMetrics()

    # Record some resolution times
    metrics.record_resolution("service1", 0.001)
    metrics.record_resolution("service1", 0.002)
    metrics.record_resolution("service2", 0.003)

    # Test average calculation
    avg1 = metrics.get_average_resolution_time("service1")
    assert avg1 == 0.0015  # (0.001 + 0.002) / 2

    avg2 = metrics.get_average_resolution_time("service2")
    assert avg2 == 0.003

    # Test cache hit ratio
    metrics.cache_hits = 8
    metrics.cache_misses = 2

    hit_ratio = metrics.get_cache_hit_ratio()
    assert hit_ratio == 0.8  # 8 / (8 + 2)
