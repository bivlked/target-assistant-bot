"""
Dependency Injection Container

Central dependency injection container for the Target Assistant Bot.
Implements Inversion of Control pattern for modular architecture.
Enhanced with performance optimizations for faster resolution.
"""

from typing import Dict, Any, Type, TypeVar, Callable, Optional, Protocol, List, Set
from functools import wraps, lru_cache
import inspect
import asyncio
import time
from collections import defaultdict


T = TypeVar("T")


class InjectionError(Exception):
    """Exception raised when dependency injection fails"""

    pass


class Lifetime:
    """Dependency lifetime management"""

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class PerformanceMetrics:
    """Performance metrics for DI container"""

    def __init__(self):
        self.resolution_times: Dict[str, List[float]] = defaultdict(list)
        self.cache_hits = 0
        self.cache_misses = 0

    def record_resolution(self, service_key: str, duration: float):
        """Record service resolution time"""
        self.resolution_times[service_key].append(duration)

    def get_average_resolution_time(self, service_key: str) -> float:
        """Get average resolution time for service"""
        times = self.resolution_times.get(service_key, [])
        return sum(times) / len(times) if times else 0.0

    def get_cache_hit_ratio(self) -> float:
        """Get cache hit ratio"""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


class DependencyContainer:
    """
    Enhanced Dependency injection container

    Manages service registration, resolution, and lifetime.
    Supports constructor injection and interface-based dependencies.
    Optimized for high-performance resolution with caching and batch operations.
    """

    def __init__(self):
        self._services: Dict[str, Dict[str, Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._scoped_instances: Dict[str, Dict[str, Any]] = {}
        self._scope_id = 0

        # Performance optimizations
        self._service_keys_cache: Dict[Type, str] = {}
        self._constructor_cache: Dict[Type, inspect.Signature] = {}
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._metrics = PerformanceMetrics()

        # Batch resolution support
        self._batch_resolving = False
        self._batch_instances: Dict[str, Any] = {}

    def register_singleton(
        self, interface: Type[T], implementation: Type[T]
    ) -> "DependencyContainer":
        """
        Register singleton service

        Args:
            interface: Interface/abstract class
            implementation: Concrete implementation

        Returns:
            DependencyContainer: Self for chaining
        """
        return self._register(interface, implementation, Lifetime.SINGLETON)

    def register_transient(
        self, interface: Type[T], implementation: Type[T]
    ) -> "DependencyContainer":
        """
        Register transient service (new instance each time)

        Args:
            interface: Interface/abstract class
            implementation: Concrete implementation

        Returns:
            DependencyContainer: Self for chaining
        """
        return self._register(interface, implementation, Lifetime.TRANSIENT)

    def register_scoped(
        self, interface: Type[T], implementation: Type[T]
    ) -> "DependencyContainer":
        """
        Register scoped service (single instance per scope)

        Args:
            interface: Interface/abstract class
            implementation: Concrete implementation

        Returns:
            DependencyContainer: Self for chaining
        """
        return self._register(interface, implementation, Lifetime.SCOPED)

    def register_instance(
        self, interface: Type[T], instance: T
    ) -> "DependencyContainer":
        """
        Register specific instance

        Args:
            interface: Interface/abstract class
            instance: Pre-created instance

        Returns:
            DependencyContainer: Self for chaining
        """
        key = self._get_key_optimized(interface)
        self._instances[key] = instance
        self._services[key] = {
            "implementation": type(instance),
            "lifetime": Lifetime.SINGLETON,
            "instance": instance,
        }
        return self

    def register_factory(
        self, interface: Type[T], factory: Callable[[], T]
    ) -> "DependencyContainer":
        """
        Register factory function

        Args:
            interface: Interface/abstract class
            factory: Factory function that creates instances

        Returns:
            DependencyContainer: Self for chaining
        """
        key = self._get_key_optimized(interface)
        self._services[key] = {"factory": factory, "lifetime": Lifetime.TRANSIENT}
        return self

    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve service instance with performance optimization

        Args:
            interface: Interface/abstract class to resolve

        Returns:
            T: Service instance

        Raises:
            InjectionError: If service cannot be resolved
        """
        start_time = time.perf_counter()

        try:
            result = self._resolve_optimized(interface)
            duration = time.perf_counter() - start_time
            self._metrics.record_resolution(
                self._get_key_optimized(interface), duration
            )
            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            self._metrics.record_resolution(
                f"FAILED_{self._get_key_optimized(interface)}", duration
            )
            raise

    def resolve_batch(self, interfaces: List[Type]) -> Dict[Type, Any]:
        """
        Resolve multiple services in batch for better performance

        Args:
            interfaces: List of interfaces to resolve

        Returns:
            Dict[Type, Any]: Dictionary mapping interfaces to resolved instances
        """
        start_time = time.perf_counter()

        self._batch_resolving = True
        self._batch_instances = {}

        try:
            results = {}
            for interface in interfaces:
                results[interface] = self._resolve_optimized(interface)

            duration = time.perf_counter() - start_time
            self._metrics.record_resolution("BATCH_RESOLUTION", duration)

            return results
        finally:
            self._batch_resolving = False
            self._batch_instances.clear()

    async def resolve_async(self, interface: Type[T]) -> T:
        """
        Resolve service instance asynchronously

        Args:
            interface: Interface/abstract class to resolve

        Returns:
            T: Service instance
        """
        return self.resolve(interface)

    def create_scope(self) -> "DependencyScope":
        """
        Create new dependency scope

        Returns:
            DependencyScope: New scope context manager
        """
        return DependencyScope(self)

    def clear_scope(self, scope_id: str) -> None:
        """
        Clear scoped instances for given scope

        Args:
            scope_id: Scope identifier
        """
        if scope_id in self._scoped_instances:
            del self._scoped_instances[scope_id]

    def is_registered(self, interface: Type[T]) -> bool:
        """
        Check if service is registered

        Args:
            interface: Interface/abstract class to check

        Returns:
            bool: True if registered, False otherwise
        """
        key = self._get_key_optimized(interface)
        return key in self._services

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get container performance metrics"""
        return self._metrics

    def clear_caches(self) -> None:
        """Clear internal caches for memory optimization"""
        self._service_keys_cache.clear()
        self._constructor_cache.clear()
        self._dependency_graph.clear()

    def _resolve_optimized(self, interface: Type[T]) -> T:
        """Optimized resolution with caching and batch support"""
        key = self._get_key_optimized(interface)

        if key not in self._services:
            self._metrics.cache_misses += 1
            raise InjectionError(f"Service {interface.__name__} not registered")

        self._metrics.cache_hits += 1
        service_config = self._services[key]
        lifetime = service_config["lifetime"]

        # Check batch resolution cache first
        if self._batch_resolving and key in self._batch_instances:
            return self._batch_instances[key]

        # Return existing singleton instance
        if lifetime == Lifetime.SINGLETON and key in self._instances:
            return self._instances[key]

        # Return existing scoped instance
        if lifetime == Lifetime.SCOPED:
            scope_instances = self._scoped_instances.get(str(self._scope_id), {})
            if key in scope_instances:
                return scope_instances[key]

        # Create new instance
        instance = self._create_instance_optimized(service_config, interface)

        # Store in batch cache if batch resolving
        if self._batch_resolving:
            self._batch_instances[key] = instance

        # Store singleton instance
        if lifetime == Lifetime.SINGLETON:
            self._instances[key] = instance

        # Store scoped instance
        elif lifetime == Lifetime.SCOPED:
            if str(self._scope_id) not in self._scoped_instances:
                self._scoped_instances[str(self._scope_id)] = {}
            self._scoped_instances[str(self._scope_id)][key] = instance

        return instance

    def _register(
        self, interface: Type[T], implementation: Type[T], lifetime: str
    ) -> "DependencyContainer":
        """Internal service registration with dependency graph building"""
        key = self._get_key_optimized(interface)

        # Validate implementation
        if not issubclass(implementation, interface):
            raise InjectionError(
                f"{implementation.__name__} does not implement {interface.__name__}"
            )

        self._services[key] = {"implementation": implementation, "lifetime": lifetime}

        # Build dependency graph for optimization
        self._build_dependency_graph(implementation, key)

        return self

    def _build_dependency_graph(self, implementation: Type, service_key: str) -> None:
        """Build dependency graph for circular dependency detection and optimization"""
        sig = self._get_constructor_signature(implementation)

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            if param.annotation and param.annotation != inspect.Parameter.empty:
                dep_key = self._get_key_optimized(param.annotation)
                self._dependency_graph[service_key].add(dep_key)

    def _create_instance_optimized(
        self, service_config: Dict[str, Any], interface: Type[T]
    ) -> T:
        """Create service instance with optimized dependency injection"""

        # Use factory if provided
        if "factory" in service_config:
            return service_config["factory"]()

        # Use existing instance if provided
        if "instance" in service_config:
            return service_config["instance"]

        implementation = service_config["implementation"]

        # Get cached constructor signature
        sig = self._get_constructor_signature(implementation)
        params = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # Skip parameters with default values
            if param.default is not inspect.Parameter.empty:
                continue

            # Resolve dependency
            if param.annotation and param.annotation != inspect.Parameter.empty:
                try:
                    dependency = self._resolve_optimized(param.annotation)
                    params[param_name] = dependency
                except InjectionError as e:
                    raise InjectionError(
                        f"Cannot resolve dependency {param.annotation.__name__} for {implementation.__name__}: {str(e)}"
                    )
            else:
                raise InjectionError(
                    f"Parameter {param_name} in {implementation.__name__} has no type annotation"
                )

        try:
            return implementation(**params)
        except Exception as e:
            raise InjectionError(
                f"Failed to create instance of {implementation.__name__}: {str(e)}"
            )

    def _get_key_optimized(self, interface: Type[T]) -> str:
        """Get service key with caching optimization"""
        if interface in self._service_keys_cache:
            return self._service_keys_cache[interface]

        key = f"{interface.__module__}.{interface.__name__}"
        self._service_keys_cache[interface] = key
        return key

    def _get_constructor_signature(self, implementation: Type) -> inspect.Signature:
        """Get constructor signature with caching"""
        if implementation in self._constructor_cache:
            return self._constructor_cache[implementation]

        sig = inspect.signature(implementation.__init__)
        self._constructor_cache[implementation] = sig
        return sig

    def _get_key(self, interface: Type[T]) -> str:
        """Get service key from interface (legacy method)"""
        return self._get_key_optimized(interface)


class DependencyScope:
    """
    Dependency scope context manager

    Manages scoped service lifetimes within a specific context.
    """

    def __init__(self, container: DependencyContainer):
        self.container = container
        self.scope_id = str(container._scope_id)
        container._scope_id += 1

    def __enter__(self) -> "DependencyScope":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.container.clear_scope(self.scope_id)

    def resolve(self, interface: Type[T]) -> T:
        """Resolve service within this scope"""
        return self.container.resolve(interface)


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """
    Get global dependency container

    Returns:
        DependencyContainer: Global container instance
    """
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container


def configure_container() -> DependencyContainer:
    """
    Configure and return the dependency container

    Returns:
        DependencyContainer: Configured container
    """
    return get_container()


def inject(interface: Type[T]) -> Callable:
    """
    Decorator for dependency injection

    Args:
        interface: Interface to inject

    Returns:
        Callable: Decorated function with injected dependency
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            container = get_container()
            dependency = container.resolve(interface)
            return func(dependency, *args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            container = get_container()
            dependency = await container.resolve_async(interface)
            if asyncio.iscoroutinefunction(func):
                return await func(dependency, *args, **kwargs)
            return func(dependency, *args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper

    return decorator


class ServiceProvider(Protocol):
    """Protocol for service providers that configure dependencies"""

    def configure(self, container: DependencyContainer) -> None:
        """Configure dependencies in the container"""
        ...
