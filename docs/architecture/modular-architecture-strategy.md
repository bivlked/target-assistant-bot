# Target Assistant Bot - Modular Architecture Strategy

## 🏗️ Architecture Decision Record

**Status**: Approved (Creative Phase 2)  
**Date**: 2025-01-08  
**Decision**: Implement Modular Monolith with Service Layer  

## 📋 Context

Target Assistant Bot требует architectural refactoring для улучшения maintainability, testability, и scalability при сохранении production stability.

### Current Architecture Challenges
- **Code Duplication**: Multiple similar patterns в handlers и utilities
- **Tight Coupling**: Direct dependencies между components без clear interfaces
- **Inconsistent Error Handling**: Various error handling approaches через codebase
- **Limited Scalability**: Current architecture ограничивает future feature expansion
- **Testing Complexity**: Difficult unit testing из-за tightly coupled components

### Requirements
- **Maintainable Architecture**: Clear separation of concerns и component boundaries
- **Testable Design**: Easy unit testing с mock dependencies
- **Scalable Structure**: Support для future features без major refactoring
- **Performance Preservation**: Maintain existing <200ms response characteristics
- **Migration Safety**: Gradual refactoring без service disruption

## 🎯 Architectural Decision

### Selected Approach: Modular Monolith with Service Layer

**Rationale**:
1. **Optimal Risk/Benefit Balance**: Significant improvements с manageable implementation risk
2. **Production Safety**: Gradual migration compatible с continuous operation
3. **Team Feasibility**: Reasonable learning curve для current development practices
4. **Future-Proof**: Foundation для potential microservices transition
5. **Testing Enhancement**: Clear boundaries enable better unit testing

### Target Architecture

```
TargetBot/
├── domain/              # Business entities and domain logic
│   ├── entities/        # Goal, Task, User domain models
│   ├── services/        # Domain services
│   └── interfaces/      # Domain abstractions
├── application/         # Use cases and application services
│   ├── services/        # Application services
│   ├── use_cases/       # Business use cases
│   └── interfaces/      # Application interfaces
├── infrastructure/      # External dependencies
│   ├── telegram/        # Telegram bot integration
│   ├── openai/         # LLM integration
│   ├── sheets/         # Google Sheets integration
│   └── persistence/    # Data persistence layer
├── presentation/       # User interface layer
│   ├── handlers/       # Telegram event handlers
│   ├── formatters/     # Message formatting
│   └── validators/     # Input validation
└── shared/            # Cross-cutting concerns
    ├── config/        # Configuration management
    ├── logging/       # Logging infrastructure
    └── exceptions/    # Custom exceptions
```

## 🔧 Migration Strategy

### Phase 1: Foundation Setup (Week 1)
- Create core abstractions и interfaces
- Implement dependency injection container
- Setup shared infrastructure (config, logging, exceptions)

### Phase 2: Service Layer Implementation (Week 1-2)
- Implement domain entities и services
- Create application services
- Migrate core business logic

### Phase 3: Infrastructure Adaptation (Week 2)
- Adapt existing external integrations
- Implement repository patterns
- Update handlers для new architecture

## 💻 Implementation Examples

### Domain Entity Example
```python
# domain/entities/goal.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class Goal:
    id: str
    user_id: int
    title: str
    description: Optional[str]
    deadline: datetime
    created_at: datetime
    updated_at: datetime
    tasks: List['Task'] = None
    
    def add_task(self, task: 'Task') -> None:
        """Add task to goal"""
        if self.tasks is None:
            self.tasks = []
        self.tasks.append(task)
    
    def calculate_progress(self) -> float:
        """Calculate goal completion percentage"""
        if not self.tasks:
            return 0.0
        
        completed_tasks = sum(1 for task in self.tasks if task.is_completed)
        return (completed_tasks / len(self.tasks)) * 100
```

### Repository Interface
```python
# domain/interfaces/goal_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.goal import Goal

class GoalRepository(ABC):
    @abstractmethod
    async def create(self, goal: Goal) -> Goal:
        """Create new goal"""
        pass
    
    @abstractmethod
    async def get_by_id(self, goal_id: str) -> Optional[Goal]:
        """Get goal by ID"""
        pass
    
    @abstractmethod  
    async def get_user_goals(self, user_id: int) -> List[Goal]:
        """Get all goals for user"""
        pass
    
    @abstractmethod
    async def update(self, goal: Goal) -> Goal:
        """Update existing goal"""
        pass
    
    @abstractmethod
    async def delete(self, goal_id: str) -> bool:
        """Delete goal"""
        pass
```

### Application Service
```python
# application/services/goal_service.py
from typing import List
from domain.interfaces.goal_repository import GoalRepository
from domain.entities.goal import Goal
from shared.exceptions.base import GoalServiceException

class GoalService:
    def __init__(self, goal_repository: GoalRepository):
        self._goal_repository = goal_repository
    
    async def create_goal(self, user_id: int, title: str, deadline: str) -> Goal:
        """Create new goal for user"""
        try:
            # Business logic validation
            if not title.strip():
                raise GoalServiceException("Goal title cannot be empty")
            
            # Create domain entity
            goal = Goal(
                user_id=user_id,
                title=title.strip(),
                deadline=self._parse_deadline(deadline)
            )
            
            # Persist через repository
            return await self._goal_repository.create(goal)
            
        except Exception as e:
            raise GoalServiceException(f"Failed to create goal: {str(e)}")
    
    async def get_user_goals(self, user_id: int) -> List[Goal]:
        """Get all goals for user"""
        return await self._goal_repository.get_user_goals(user_id)
```

### Dependency Injection Container
```python
# shared/container.py
from typing import Dict, TypeVar, Type, get_type_hints
from dataclasses import dataclass
import inspect

T = TypeVar('T')

@dataclass
class Container:
    _services: Dict[Type, object] = None
    _singletons: Dict[Type, object] = None
    
    def __post_init__(self):
        if self._services is None:
            self._services = {}
        if self._singletons is None:
            self._singletons = {}
    
    def register(self, interface: Type[T], implementation: T, singleton: bool = False) -> None:
        """Register service implementation"""
        if singleton:
            self._singletons[interface] = implementation
        else:
            self._services[interface] = implementation
    
    def get(self, interface: Type[T]) -> T:
        """Get service instance"""
        # Check singletons first
        if interface in self._singletons:
            return self._singletons[interface]
        
        # Check registered services
        if interface in self._services:
            service = self._services[interface]
            
            # Auto-wire dependencies if service is a class
            if inspect.isclass(service):
                return self._create_instance(service)
            
            return service
        
        raise ValueError(f"Service not registered: {interface}")
    
    def _create_instance(self, service_class: Type[T]) -> T:
        """Create instance with dependency injection"""
        # Get constructor parameters
        signature = inspect.signature(service_class.__init__)
        args = {}
        
        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue
                
            # Get parameter type
            param_type = param.annotation
            if param_type and param_type != inspect.Parameter.empty:
                args[param_name] = self.get(param_type)
        
        return service_class(**args)
```

### Error Handling Standardization
```python
# shared/exceptions/base.py
class TargetBotException(Exception):
    """Base exception for Target Bot"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class GoalServiceException(TargetBotException):
    """Goal service specific exceptions"""
    pass

class TaskServiceException(TargetBotException):
    """Task service specific exceptions"""
    pass

class ExternalServiceException(TargetBotException):
    """External service integration exceptions"""
    pass

class ValidationException(TargetBotException):
    """Input validation exceptions"""
    pass
```

### Configuration Management
```python
# shared/config/settings.py
from pydantic import BaseSettings, Field
from typing import List, Optional

class Settings(BaseSettings):
    # Application
    app_name: str = "Target Assistant Bot"
    app_version: str = "0.2.3"
    debug: bool = False
    
    # Telegram Bot
    telegram_token: str = Field(..., env="TELEGRAM_TOKEN")
    telegram_webhook_url: Optional[str] = Field(None, env="TELEGRAM_WEBHOOK_URL")
    
    # OpenAI
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-mini", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(1000, env="OPENAI_MAX_TOKENS")
    
    # Google Sheets
    sheets_credentials_file: str = Field("google_credentials.json", env="SHEETS_CREDENTIALS_FILE")
    sheets_scope: List[str] = ["https://www.googleapis.com/auth/spreadsheets"]
    
    # Database/Storage
    storage_type: str = Field("sheets", env="STORAGE_TYPE")  # sheets, sqlite, postgres
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    prometheus_port: int = Field(8000, env="PROMETHEUS_PORT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()
```

## 🧪 Testing Strategy Integration

### Mock-Based Unit Testing
```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, AsyncMock
from shared.container import Container
from domain.interfaces.goal_repository import GoalRepository
from application.services.goal_service import GoalService

@pytest.fixture
def mock_container():
    """Test container with mocked dependencies"""
    container = Container()
    
    # Mock repositories
    mock_goal_repo = AsyncMock(spec=GoalRepository)
    container.register(GoalRepository, mock_goal_repo, singleton=True)
    
    return container

@pytest.fixture
def goal_service(mock_container):
    """Goal service with mocked dependencies"""
    return mock_container.get(GoalService)

@pytest.fixture
async def sample_goal():
    """Sample goal entity for testing"""
    return Goal(
        id="test-goal-1",
        user_id=12345,
        title="Test Goal",
        description="Test Description",
        deadline=datetime.now() + timedelta(days=30),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
```

## 📊 Migration Safety Measures

### Feature Flags
```python
# shared/feature_flags.py
from enum import Enum
from shared.config.settings import settings

class FeatureFlag(Enum):
    NEW_ARCHITECTURE = "new_architecture"
    SERVICE_LAYER = "service_layer"
    NEW_ERROR_HANDLING = "new_error_handling"

class FeatureToggle:
    @staticmethod
    def is_enabled(flag: FeatureFlag) -> bool:
        """Check if feature flag is enabled"""
        # Read from environment или configuration
        return getattr(settings, f"FEATURE_{flag.value.upper()}", False)
    
    @staticmethod
    def with_fallback(flag: FeatureFlag, new_implementation, old_implementation):
        """Execute new or old implementation based on feature flag"""
        if FeatureToggle.is_enabled(flag):
            return new_implementation()
        return old_implementation()
```

### Rollback Strategy
- **Parallel Implementation**: Old и new code работают simultaneously
- **Gradual Migration**: Component-by-component migration
- **Monitoring**: Performance и error rate monitoring
- **Quick Rollback**: Ability to disable new architecture via feature flags

## 📈 Success Metrics

### Technical Metrics
- **Test Coverage**: Maintain 97.55%+ during migration
- **Response Time**: Keep <200ms performance
- **Error Rate**: No increase in production errors
- **Code Quality**: Improve MyPy strict mode compliance

### Architectural Metrics
- **Component Coupling**: Reduce inter-component dependencies
- **Code Duplication**: Eliminate duplicate patterns
- **Test Isolation**: Achieve 100% unit test isolation
- **Maintainability**: Improve code maintainability scores

## 🔄 Next Steps

1. **Begin Phase 1**: Setup foundation (Week 1)
2. **Monitor Migration**: Track metrics и user impact
3. **Iterate Based on Feedback**: Adjust approach as needed
4. **Complete Migration**: Full transition to new architecture
5. **Documentation**: Update architectural documentation

---

**Created**: 2025-01-08 (Creative Phase 2)  
**Team**: Architecture Enhancement Team  
**Review Date**: 2025-02-08 