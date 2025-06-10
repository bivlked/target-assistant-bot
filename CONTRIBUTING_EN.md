---
language: en
type: guide
audience: contributor
difficulty: beginner
last_updated: 2025-06-10
english_version: CONTRIBUTING_EN.md
russian_version: CONTRIBUTING.md
---

# 🤝 Contributing Guide

<div align="center">
  <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/People%20with%20professions/Technologist.png" width="100">
  
  <p>
    <strong>Target Assistant Bot - Contribution Guide</strong><br>
    <sub>Welcome to our development team!</sub>
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

Thank you for wanting to help develop Target Assistant Bot! We value any contribution and maintain high quality standards to create an enterprise-grade solution.

---

## 🎯 Architectural Principles

Target Assistant Bot follows **Clean Architecture** and **Quality-First Development**. Before starting work, be sure to review:

### 📚 Required Reading
- **[📋 README.md](README.md)** - Project description and quick start
- **[📋 DEVELOPMENT_CHECKLIST.md](DEVELOPMENT_CHECKLIST.md)** - Roadmap, architecture and quality standards
- **[📝 CHANGELOG.md](CHANGELOG.md)** - Change history and current status
- **[🤝 CONTRIBUTING.md](CONTRIBUTING.md)** - Development guide (this document)

---

## 🚀 Quick Start

### Environment Requirements
- **Python 3.11+** (recommended 3.12+, minimum 3.11)
- **Git 2.25+** with configured pre-commit hooks
- **Poetry** (recommended) or `pip` with virtual environment

### Environment Setup

#### Option 1: Poetry (recommended)
```bash
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
poetry install --with dev
poetry shell
pre-commit install
```

#### Option 2: pip + venv
```bash
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
pre-commit install
```

---

## 🔄 Git Workflow

### 1. 🍴 Preparation
```bash
# Fork the repository through GitHub UI
git clone https://github.com/YOUR_USERNAME/target-assistant-bot.git
git remote add upstream https://github.com/bivlked/target-assistant-bot.git
```

### 2. 🌿 Create Feature Branch
```bash
# Sync with upstream
git checkout main
git fetch upstream
git rebase upstream/main

# Create feature branch
git checkout -b feat/your-feature-name
```

#### Naming Convention
- **Features**: `feat/brief-description`
- **Bug fixes**: `fix/problem-description`
- **Documentation**: `docs/topic`
- **Refactoring**: `refactor/component`
- **Tests**: `test/component`

### 3. 💻 Development

#### Quality Standards
- **Code in English** (variables, functions, comments)
- **UI in Russian** (user interface)
- **Type hints required** for all functions
- **Tests** for all new functionality
- **High test coverage** (current project level: 94.49%)

### 4. 🧪 Required Checks
```bash
# Automatic checks (pre-commit)
black .                    # Code formatting
ruff check .              # Linting
mypy .                    # Type checking
pytest -xvs              # Basic tests

# Full testing
pytest --cov=. --cov-report=html --cov-fail-under=95
```

### 5. 📝 Commits (Conventional Commits)
```bash
# Examples of correct messages
feat(goal-manager): add support for goal prioritization
fix(llm-client): resolve timeout handling in async requests
docs(architecture): update clean architecture documentation
test(handlers): add integration tests for goal creation
```

### 6. 🔄 Pull Request
```bash
git push origin feat/your-feature-name
# Create PR through GitHub UI
```

---

## 📋 Quality Gates

### ✅ Required criteria for merge
- **100% Type coverage** - all functions have type hints
- **MyPy in strict mode** - no warnings
- **High test coverage** - maintain current level (94.49%)
- **Clean Architecture** - follow layers and dependency rules
- **Code review approved** - minimum one approval from maintainer

---

## 🏗️ Architectural Guidelines

### Clean Architecture Layers
```
📱 Presentation Layer    (handlers/, main.py)
🔧 Application Layer     (core/goal_manager.py)
💼 Domain Layer          (core/models.py)
🗄️ Infrastructure Layer  (sheets/, llm/, utils/)
```

### Dependency Injection
```python
# ✅ Correct: Clean Architecture
from core.interfaces import AsyncStorageInterface

class GoalService:
    def __init__(self, storage: AsyncStorageInterface) -> None:
        self._storage = storage

# ❌ Incorrect: Direct dependency
import gspread
class GoalService:
    def __init__(self):
        self.client = gspread.service_account()
```

---

## 🧪 Testing Guidelines

### Test Structure (testing pyramid)
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

## 📞 Getting Help

### Communication Channels
- **GitHub Issues** - bugs, feature requests
- **GitHub Discussions** - architectural questions
- **Pull Request Reviews** - specific code questions

### Response Time Expectations
- **Critical bugs** - within 24 hours
- **Feature requests** - within 1 week
- **Code reviews** - within 2 business days

---

## 📜 Code of Conduct

We follow the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

### Our Values
- **Respect** - respect for all participants
- **Constructive feedback** - constructive criticism
- **Collaboration** - teamwork
- **Learning** - continuous learning and growth

---

<div align="center">
  <h2>🙏 Thank you for your contribution!</h2>
  <p>
    <strong>Target Assistant Bot</strong> becomes better thanks to developers like you.<br>
    <sub>Together we create an enterprise-grade solution for achieving goals!</sub>
  </p>
</div>

---

**Last Updated**: 2025-06-10  
**Document Version**: v0.2.5 Enhanced Bilingual  
**Supports Project**: v0.2.5+ 