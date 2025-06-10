#!/usr/bin/env python3
"""
API Documentation Generator

Автоматически генерирует API документацию из Python кода
согласно архитектуре Enhanced GitHub-Native Documentation System.
"""

import ast
import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class APIDocumentationGenerator:
    """
    Generate API documentation automatically from code
    """

    def __init__(self, source_dir: str = ".", output_dir: str = "docs/api"):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.api_endpoints: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []

    def discover_api_endpoints(self) -> List[Dict[str, Any]]:
        """Scan code для API endpoints"""
        print("🔍 Discovering API endpoints...")

        endpoints: List[Dict[str, Any]] = []

        # Scan Python files for API patterns
        for python_file in self.source_dir.rglob("*.py"):
            if "test" in str(python_file) or "__pycache__" in str(python_file):
                continue

            try:
                with open(python_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Parse AST for detailed analysis
                tree = ast.parse(content, filename=str(python_file))

                for node in ast.walk(tree):
                    # Look for class definitions (potential API classes)
                    if isinstance(node, ast.ClassDef):
                        class_info = self._extract_class_info(node, python_file)
                        if class_info:
                            self.classes.append(class_info)

                    # Look for function definitions (potential API methods)
                    elif isinstance(node, ast.FunctionDef):
                        func_info = self._extract_function_info(node, python_file)
                        if func_info:
                            self.functions.append(func_info)

            except Exception as e:
                print(f"⚠️  Error parsing {python_file}: {e}")
                continue

        self.api_endpoints = endpoints
        return endpoints

    def _extract_class_info(
        self, node: ast.ClassDef, file_path: Path
    ) -> Optional[Dict[str, Any]]:
        """Extract information about a class"""
        docstring = ast.get_docstring(node)

        # Check if this looks like an API-related class
        api_indicators = ["handler", "client", "manager", "service", "api", "interface"]
        class_name_lower = node.name.lower()

        if not any(indicator in class_name_lower for indicator in api_indicators):
            return None

        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self._extract_function_info(
                    item, file_path, is_method=True
                )
                if method_info:
                    methods.append(method_info)

        return {
            "type": "class",
            "name": node.name,
            "docstring": docstring or f"API class: {node.name}",
            "file_path": str(file_path.relative_to(self.source_dir)),
            "line_number": node.lineno,
            "methods": methods,
            "bases": [
                base.id if isinstance(base, ast.Name) else str(base)
                for base in node.bases
            ],
        }

    def _extract_function_info(
        self, node: ast.FunctionDef, file_path: Path, is_method: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Extract information about a function or method"""
        docstring = ast.get_docstring(node)

        # Skip private methods and special methods (except __init__)
        if node.name.startswith("_") and node.name != "__init__":
            return None

        # Extract parameters
        parameters = []
        for arg in node.args.args:
            param_info = {"name": arg.arg, "annotation": None, "default": None}

            # Get type annotation if available
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    param_info["annotation"] = arg.annotation.id
                else:
                    try:
                        param_info["annotation"] = ast.unparse(arg.annotation)
                    except Exception:
                        param_info["annotation"] = str(arg.annotation)

            parameters.append(param_info)

        # Extract defaults
        defaults = node.args.defaults
        if defaults:
            # Match defaults to parameters (defaults are for the last N parameters)
            param_count = len(parameters)
            default_count = len(defaults)
            start_idx = param_count - default_count

            for i, default in enumerate(defaults):
                param_idx = start_idx + i
                if param_idx < len(parameters):
                    try:
                        parameters[param_idx]["default"] = ast.unparse(default)
                    except Exception:
                        parameters[param_idx]["default"] = str(default)

        # Extract return annotation
        return_annotation = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return_annotation = node.returns.id
            else:
                try:
                    return_annotation = ast.unparse(node.returns)
                except Exception:
                    return_annotation = str(node.returns)

        return {
            "type": "method" if is_method else "function",
            "name": node.name,
            "docstring": docstring
            or f"{'Method' if is_method else 'Function'}: {node.name}",
            "file_path": str(file_path.relative_to(self.source_dir)),
            "line_number": node.lineno,
            "parameters": parameters,
            "return_annotation": return_annotation,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
        }

    def generate_api_docs(self) -> None:
        """Generate comprehensive API documentation"""
        print("📚 Generating API documentation...")

        # Discover all API components
        self.discover_api_endpoints()

        # Generate overview document
        self._generate_api_overview()

        # Generate detailed documentation for each component
        self._generate_class_docs()
        self._generate_function_docs()

        # Generate index
        self._generate_api_index()

        print(f"✅ API documentation generated in {self.output_dir}")

    def _generate_api_overview(self) -> None:
        """Generate API overview document"""
        content = f"""---
language: ru
type: api
audience: developer
difficulty: intermediate
last_updated: {datetime.now().strftime('%Y-%m-%d')}
english_version: api-overview_EN.md
russian_version: api-overview.md
---

# 🔌 API Справочник: Target Assistant Bot

> **Версия API**: v0.2.5  
> **Последнее обновление**: {datetime.now().strftime('%Y-%m-%d')}  
> **Статус**: ✅ Стабильный

## 📋 Обзор

Target Assistant Bot предоставляет комплексный API для управления целями, задачами и интеграции с внешними сервисами.

**Архитектура**: Clean Architecture с четким разделением слоев
**Технологии**: Python 3.12+, Async/Await, Type Hints

## 📊 Статистика API

| Компонент | Количество | Описание |
|-----------|------------|----------|
| **Классы** | {len(self.classes)} | API классы и сервисы |
| **Функции** | {len(self.functions)} | Публичные функции |
| **Endpoints** | {len(self.api_endpoints)} | Обнаруженные endpoints |

## 🏗️ Архитектурные слои

### 📱 Presentation Layer
Обработчики Telegram бота и форматирование ответов

### 🔧 Application Layer  
Бизнес-логика и оркестрация сервисов

### 💼 Domain Layer
Основные модели и бизнес-правила

### 🗄️ Infrastructure Layer
Интеграции с внешними сервисами (OpenAI, Google Sheets)

## 📚 Основные компоненты

### 🎯 Goal Management API
Управление целями пользователей
- Создание и редактирование целей
- Отслеживание прогресса
- Аналитика достижений

### 📝 Task Management API
Управление задачами в рамках целей
- Ежедневные задачи
- Статусы выполнения
- Планирование

### 🧠 LLM Integration API
Интеграция с языковыми моделями
- Генерация планов
- Мотивационные сообщения
- Анализ прогресса

### 📊 Analytics API
Сбор и анализ статистики
- Метрики выполнения
- Отчеты по целям
- Прогнозирование

## 🔐 Аутентификация

```python
# Пример использования API
from core.goal_manager import GoalManager
from shared.container.dependency_container import Container

# Получение экземпляра через DI контейнер
container = Container()
goal_manager = container.resolve(GoalManager)

# Использование API
goal = await goal_manager.create_goal(user_id, goal_data)
```

## 📖 Дополнительная документация

- [📋 Классы и интерфейсы](classes.md)
- [⚡ Функции и методы](functions.md)
- [🧪 Примеры использования](examples.md)

## 🤝 Внесение изменений

При изменении API обязательно:
1. Обновите документацию
2. Добавьте тесты
3. Проверьте обратную совместимость
4. Обновите примеры

---

**📝 Автоматическая генерация:**  
Этот документ автоматически сгенерирован {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} из исходного кода.
"""

        with open(self.output_dir / "api-overview.md", "w", encoding="utf-8") as f:
            f.write(content)

    def _generate_class_docs(self) -> None:
        """Generate documentation for classes"""
        if not self.classes:
            return

        content = f"""---
language: ru
type: api
audience: developer
difficulty: intermediate
last_updated: {datetime.now().strftime('%Y-%m-%d')}
english_version: classes_EN.md
russian_version: classes.md
---

# 📋 API Классы и Интерфейсы

> **Обнаружено классов**: {len(self.classes)}  
> **Последнее обновление**: {datetime.now().strftime('%Y-%m-%d')}

## 📚 Список классов

"""

        for class_info in sorted(self.classes, key=lambda x: x["name"]):
            content += f"""
### 🏗️ `{class_info['name']}`

**Файл**: `{class_info['file_path']}`  
**Строка**: {class_info['line_number']}

**Описание**: {class_info['docstring']}

"""
            if class_info["bases"]:
                content += f"**Наследуется от**: {', '.join(class_info['bases'])}\n\n"

            if class_info["methods"]:
                content += "**Методы**:\n"
                for method in class_info["methods"]:
                    async_marker = "async " if method.get("is_async") else ""
                    params = ", ".join(
                        [p["name"] for p in method.get("parameters", [])]
                    )
                    return_type = (
                        f" -> {method['return_annotation']}"
                        if method.get("return_annotation")
                        else ""
                    )

                    content += (
                        f"- `{async_marker}{method['name']}({params}){return_type}`\n"
                    )
                    if method["docstring"]:
                        content += f"  - {method['docstring']}\n"
                content += "\n"

        content += f"""
---

**📝 Автоматическая генерация:**  
Документация сгенерирована {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} из исходного кода.
"""

        with open(self.output_dir / "classes.md", "w", encoding="utf-8") as f:
            f.write(content)

    def _generate_function_docs(self) -> None:
        """Generate documentation for functions"""
        if not self.functions:
            return

        content = f"""---
language: ru
type: api
audience: developer
difficulty: intermediate
last_updated: {datetime.now().strftime('%Y-%m-%d')}
english_version: functions_EN.md
russian_version: functions.md
---

# ⚡ API Функции и методы

> **Обнаружено функций**: {len(self.functions)}  
> **Последнее обновление**: {datetime.now().strftime('%Y-%m-%d')}

## 📚 Список функций

"""

        for func_info in sorted(self.functions, key=lambda x: x["name"]):
            async_marker = "async " if func_info.get("is_async") else ""
            params = ", ".join(
                [
                    f"{p['name']}: {p.get('annotation', 'Any')}"
                    + (f" = {p['default']}" if p.get("default") else "")
                    for p in func_info.get("parameters", [])
                ]
            )
            return_type = (
                f" -> {func_info['return_annotation']}"
                if func_info.get("return_annotation")
                else ""
            )

            content += f"""
### ⚡ `{async_marker}{func_info['name']}({params}){return_type}`

**Файл**: `{func_info['file_path']}`  
**Строка**: {func_info['line_number']}

**Описание**: {func_info['docstring']}

"""

            if func_info.get("parameters"):
                content += "**Параметры**:\n"
                for param in func_info["parameters"]:
                    param_type = param.get("annotation", "Any")
                    default_info = (
                        f" (по умолчанию: {param['default']})"
                        if param.get("default")
                        else ""
                    )
                    content += f"- `{param['name']}: {param_type}` {default_info}\n"
                content += "\n"

        content += f"""
---

**📝 Автоматическая генерация:**  
Документация сгенерирована {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} из исходного кода.
"""

        with open(self.output_dir / "functions.md", "w", encoding="utf-8") as f:
            f.write(content)

    def _generate_api_index(self) -> None:
        """Generate API documentation index"""
        content = f"""---
language: ru
type: api
audience: developer
difficulty: beginner
last_updated: {datetime.now().strftime('%Y-%m-%d')}
english_version: README_EN.md
russian_version: README.md
---

# 📚 API Документация - Target Assistant Bot

> **Статус**: ✅ Автоматически сгенерировано  
> **Последнее обновление**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🎯 Быстрая навигация

| Раздел | Описание | Количество |
|--------|----------|------------|
| [📋 Обзор API](api-overview.md) | Общее описание архитектуры | - |
| [🏗️ Классы](classes.md) | API классы и интерфейсы | {len(self.classes)} |
| [⚡ Функции](functions.md) | Публичные функции | {len(self.functions)} |

## 🚀 Быстрый старт

```python
# Пример использования основного API
from core.goal_manager import GoalManager
from shared.container.dependency_container import Container

# Инициализация через DI контейнер
container = Container()
goal_manager = container.resolve(GoalManager)

# Создание цели
goal_data = {{
    "title": "Изучить Python",
    "deadline": "2025-07-01",
    "priority": "high"
}}

goal = await goal_manager.create_goal(user_id=123, goal_data=goal_data)
```

## 📊 Статистика генерации

- **Время генерации**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Классов обнаружено**: {len(self.classes)}
- **Функций обнаружено**: {len(self.functions)}
- **Endpoints обнаружено**: {len(self.api_endpoints)}
- **Файлов просканировано**: {len(list(self.source_dir.rglob("*.py")))}

## 🔄 Автоматическое обновление

Эта документация автоматически генерируется из исходного кода при каждом изменении API.
Для ручного обновления выполните:

```bash
python .github/scripts/api-doc-generator.py
```

---

**🔗 Навигация:**
- 🏠 [Главная документация](../../README.md)
- 🤝 [Участие в проекте](../../CONTRIBUTING.md)
- 🔧 [Руководство разработчика](../../DEVELOPMENT_CHECKLIST.md)
"""

        with open(self.output_dir / "README.md", "w", encoding="utf-8") as f:
            f.write(content)

    def generate_statistics_report(self) -> Dict[str, Any]:
        """Generate statistics about API documentation generation"""
        python_files = list(self.source_dir.rglob("*.py"))
        total_files = len(python_files)

        report = {
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_python_files": total_files,
                "classes_found": len(self.classes),
                "functions_found": len(self.functions),
                "endpoints_found": len(self.api_endpoints),
                "documentation_files_generated": 4,  # overview, classes, functions, index
            },
            "files_scanned": [
                str(f.relative_to(self.source_dir)) for f in python_files
            ],
            "output_directory": str(self.output_dir),
        }

        return report


def main():
    """Main execution function"""
    print("🔌 API Documentation Generator")
    print("=" * 50)

    generator = APIDocumentationGenerator()

    # Generate all API documentation
    generator.generate_api_docs()

    # Generate statistics report
    report = generator.generate_statistics_report()

    # Save statistics
    with open("api-doc-generation-report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n📊 GENERATION STATISTICS:")
    stats = report["statistics"]
    print(f"   Total Python files: {stats['total_python_files']}")
    print(f"   Classes documented: {stats['classes_found']}")
    print(f"   Functions documented: {stats['functions_found']}")
    print(f"   Endpoints discovered: {stats['endpoints_found']}")
    print(f"   Documentation files: {stats['documentation_files_generated']}")

    print("\n📄 Statistics report saved to: api-doc-generation-report.json")
    print("✅ API documentation generation complete!")


if __name__ == "__main__":
    main()
