"""
Dependency Injection Container

Central dependency injection container for the Target Assistant Bot.
Implements Inversion of Control pattern for modular architecture.
"""

from typing import Dict, Any, Type, TypeVar, Callable, Optional, Protocol
from functools import wraps
import inspect
import asyncio


T = TypeVar("T")


class InjectionError(Exception):
    """Exception raised when dependency injection fails"""

    pass


class Lifetime:
    """Dependency lifetime management"""

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class DependencyContainer:
    """
    Dependency injection container

    Manages service registration, resolution, and lifetime.
    Supports constructor injection and interface-based dependencies.
    """

    def __init__(self):
        self._services: Dict[str, Dict[str, Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._scoped_instances: Dict[str, Dict[str, Any]] = {}
        self._scope_id = 0

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
        key = self._get_key(interface)
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
        key = self._get_key(interface)
        self._services[key] = {"factory": factory, "lifetime": Lifetime.TRANSIENT}
        return self

    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve service instance

        Args:
            interface: Interface/abstract class to resolve

        Returns:
            T: Service instance

        Raises:
            InjectionError: If service cannot be resolved
        """
        key = self._get_key(interface)

        if key not in self._services:
            raise InjectionError(f"Service {interface.__name__} not registered")

        service_config = self._services[key]
        lifetime = service_config["lifetime"]

        # Return existing singleton instance
        if lifetime == Lifetime.SINGLETON and key in self._instances:
            return self._instances[key]

        # Return existing scoped instance
        if lifetime == Lifetime.SCOPED:
            scope_instances = self._scoped_instances.get(str(self._scope_id), {})
            if key in scope_instances:
                return scope_instances[key]

        # Create new instance
        instance = self._create_instance(service_config, interface)

        # Store singleton instance
        if lifetime == Lifetime.SINGLETON:
            self._instances[key] = instance

        # Store scoped instance
        elif lifetime == Lifetime.SCOPED:
            if str(self._scope_id) not in self._scoped_instances:
                self._scoped_instances[str(self._scope_id)] = {}
            self._scoped_instances[str(self._scope_id)][key] = instance

        return instance

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
        key = self._get_key(interface)
        return key in self._services

    def _register(
        self, interface: Type[T], implementation: Type[T], lifetime: str
    ) -> "DependencyContainer":
        """Internal service registration"""
        key = self._get_key(interface)

        # Validate implementation
        if not issubclass(implementation, interface):
            raise InjectionError(
                f"{implementation.__name__} does not implement {interface.__name__}"
            )

        self._services[key] = {"implementation": implementation, "lifetime": lifetime}
        return self

    def _create_instance(self, service_config: Dict[str, Any], interface: Type[T]) -> T:
        """Create service instance with dependency injection"""

        # Use factory if provided
        if "factory" in service_config:
            return service_config["factory"]()

        # Use existing instance if provided
        if "instance" in service_config:
            return service_config["instance"]

        implementation = service_config["implementation"]

        # Get constructor parameters
        sig = inspect.signature(implementation.__init__)
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
                    dependency = self.resolve(param.annotation)
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

    def _get_key(self, interface: Type[T]) -> str:
        """Get service key from interface"""
        return f"{interface.__module__}.{interface.__name__}"


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
