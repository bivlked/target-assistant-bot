# 🤝 Руководство по внесению вклада

<div align="center">
  <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/People%20with%20professions/Technologist.png" width="100">
  
  <p>
    <strong>Target Assistant Bot - Contribution Guide</strong><br>
    <sub>Добро пожаловать в нашу команду разработчиков!</sub>
  </p>

  <a href="https://github.com/bivlked/target-assistant-bot/blob/main/README.md">
    <img src="https://img.shields.io/badge/📋-Project_README-blue?style=flat-square" alt="Project README">
  </a>
  <a href="https://github.com/bivlked/target-assistant-bot/blob/main/DEVELOPMENT_CHECKLIST.md">
    <img src="https://img.shields.io/badge/🏗️-Development_Checklist-green?style=flat-square" alt="Development Checklist">
  </a>
  <a href="https://github.com/bivlked/target-assistant-bot/blob/main/CHANGELOG.md">
    <img src="https://img.shields.io/badge/📝-Changelog-orange?style=flat-square" alt="Changelog">
  </a>
</div>

Спасибо, что хотите помочь развитию Target Assistant Bot! Мы ценим любой вклад и придерживаемся высоких стандартов качества для создания enterprise-grade решения.

---

## 🎯 Архитектурные принципы

Target Assistant Bot следует **Clean Architecture** и **Quality-First Development**. Перед началом работы обязательно ознакомьтесь:

### 📚 Обязательное чтение
- **[📋 README.md](README.md)** - Описание проекта и быстрый старт
- **[📋 DEVELOPMENT_CHECKLIST.md](DEVELOPMENT_CHECKLIST.md)** - Roadmap, архитектура и стандарты качества
- **[📝 CHANGELOG.md](CHANGELOG.md)** - История изменений и текущий статус
- **[🤝 CONTRIBUTING.md](CONTRIBUTING.md)** - Руководство по разработке (данный документ)

---

## 🚀 Быстрый старт

### Требования к окружению
- **Python 3.11+** (рекомендуется 3.12+, минимум 3.11)
- **Git 2.25+** с настроенными pre-commit hooks
- **Poetry** (рекомендуется) или `pip` с виртуальным окружением

### Настройка окружения

#### Вариант 1: Poetry (рекомендуется)
```bash
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
poetry install --with dev
poetry shell
pre-commit install
```

#### Вариант 2: pip + venv
```bash
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
pre-commit install
```

---

## 🔄 Рабочий процесс (Git Workflow)

### 1. 🍴 Подготовка к работе
```bash
# Форкните репозиторий через GitHub UI
git clone https://github.com/YOUR_USERNAME/target-assistant-bot.git
git remote add upstream https://github.com/bivlked/target-assistant-bot.git
```

### 2. 🌿 Создание feature ветки
```bash
# Синхронизация с upstream
git checkout main
git fetch upstream
git rebase upstream/main

# Создание feature ветки
git checkout -b feat/your-feature-name
```

#### Naming Convention
- **Features**: `feat/краткое-описание`
- **Bug fixes**: `fix/описание-проблемы`
- **Documentation**: `docs/topic`
- **Refactoring**: `refactor/component`
- **Tests**: `test/component`

### 3. 💻 Разработка

#### Стандарты качества
- **Код на английском языке** (переменные, функции, комментарии)
- **UI на русском языке** (пользовательский интерфейс)
- **Type hints обязательны** для всех функций
- **Tests** для всего нового функционала
- **High test coverage** (текущий уровень проекта: 94.49%)

### 4. 🧪 Обязательные проверки
```bash
# Автоматические проверки (pre-commit)
black .                    # Code formatting
ruff check .              # Linting
mypy .                    # Type checking
pytest -xvs              # Basic tests

# Полное тестирование
pytest --cov=. --cov-report=html --cov-fail-under=95
```

### 5. 📝 Коммиты (Conventional Commits)
```bash
# Примеры правильных сообщений
feat(goal-manager): add support for goal prioritization
fix(llm-client): resolve timeout handling in async requests
docs(architecture): update clean architecture documentation
test(handlers): add integration tests for goal creation
```

### 6. 🔄 Pull Request
```bash
git push origin feat/your-feature-name
# Создайте PR через GitHub UI
```

---

## 📋 Quality Gates (Критерии качества)

### ✅ Обязательные требования для merge
- **100% Type coverage** - все функции имеют type hints
- **MyPy в strict mode** - без warnings
- **High test coverage** - поддержание текущего уровня (94.49%)
- **Clean Architecture** - соблюдение слоев и dependency rules
- **Code review approved** - минимум одно approval от maintainer

---

## 🏗️ Архитектурные Guidelines

### Clean Architecture Layers
```
📱 Presentation Layer    (handlers/, main.py)
🔧 Application Layer     (core/goal_manager.py)
💼 Domain Layer          (core/models.py)
🗄️ Infrastructure Layer  (sheets/, llm/, utils/)
```

### Dependency Injection
```python
# ✅ Правильно: Clean Architecture
from core.interfaces import AsyncStorageInterface

class GoalService:
    def __init__(self, storage: AsyncStorageInterface) -> None:
        self._storage = storage

# ❌ Неправильно: Direct dependency
import gspread
class GoalService:
    def __init__(self):
        self.client = gspread.service_account()
```

---

## 🧪 Testing Guidelines

### Test Structure (пирамида тестирования)
```
    🔺 E2E Tests (5%)
   🔸🔸 Contract Tests (15%)
  🔹🔹🔹 Integration (30%)
 🔸🔸🔸🔸 Unit Tests (50%)
```

### Test Example
```python
class TestGoalManager:
    @pytest.fixture
    def goal_manager(self, mock_storage, mock_llm):
        return GoalManager(storage=mock_storage, llm=mock_llm)
    
    async def test_create_goal_success(self, goal_manager):
        # Given
        goal_data = {"title": "Test Goal", "priority": "high"}
        
        # When
        result = await goal_manager.create_goal(goal_data)
        
        # Then
        assert result.title == "Test Goal"
```

---

## 📖 Documentation Standards

### Code Documentation
```python
class AsyncLLMClient:
    """Asynchronous client for LLM operations.
    
    This client provides async methods for interacting with OpenAI API,
    including plan generation and motivation messages.
    
    Args:
        api_key: OpenAI API key for authentication
        model: GPT model to use (default: gpt-4o-mini)
    
    Example:
        >>> client = AsyncLLMClient(api_key="your-key")
        >>> plan = await client.generate_plan("Learn Python", days=30)
    """
    
    async def generate_plan(
        self, 
        goal: str, 
        days: int,
        priority: Priority = Priority.MEDIUM
    ) -> Plan:
        """Generate execution plan for the given goal.
        
        Args:
            goal: Goal description in natural language
            days: Number of days for plan execution
            priority: Goal priority affecting task complexity
            
        Returns:
            Plan object with organized tasks and timeline
            
        Raises:
            LLMAPIError: If API request fails
            ValidationError: If goal description is invalid
        """
        pass
```

---

## 🔒 Security Guidelines

### Secure Coding Practices
```python
# ✅ Secure: Input validation
from pydantic import BaseModel, validator

class GoalInput(BaseModel):
    title: str
    
    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Title cannot be empty')
        return v.strip()

# ✅ Secure: Environment variables
import os
def get_api_key() -> str:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError('API key not set')
    return api_key
```

---

## 🤝 Code Review Process

### Review Checklist for Authors
- [ ] Self-review completed
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Performance impact assessed
- [ ] Security considerations checked

### Review Checklist for Reviewers
- [ ] Architecture compliance
- [ ] Code quality
- [ ] Test coverage
- [ ] Performance
- [ ] Security

---

## 📞 Получение помощи

### Каналы коммуникации
- **GitHub Issues** - баги, feature requests
- **GitHub Discussions** - архитектурные вопросы
- **Pull Request Reviews** - конкретные вопросы по коду

### Ожидания по времени ответа
- **Critical bugs** - в течение 24 часов
- **Feature requests** - в течение 1 недели
- **Code reviews** - в течение 2 рабочих дней

---

## 📜 Кодекс поведения

Мы придерживаемся [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

### Наши ценности
- **Respect** - уважение ко всем участникам
- **Constructive feedback** - конструктивная критика
- **Collaboration** - работа в команде
- **Learning** - постоянное обучение и рост

---

<div align="center">
  <h2>🙏 Спасибо за ваш вклад!</h2>
  <p>
    <strong>Target Assistant Bot</strong> становится лучше благодаря таким разработчикам как вы.<br>
    <sub>Вместе мы создаем enterprise-grade решение для достижения целей!</sub>
  </p>
</div>

---

**Последнее обновление**: 2025-06-09  
**Версия документа**: v0.2.3 Enhanced  
**Соответствует проекту**: v0.2.3+ 