# 📝 Changelog

<div align="center">
  <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Scroll.png" width="100">
  
  <p>
    <strong>История изменений Target Assistant Bot</strong><br>
    <sub>Все значимые изменения документируются в этом файле</sub>
  </p>
</div>

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и проект придерживается [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.3] - 2025-01-18

<div align="center">
  <a href="https://github.com/bivlked/target-assistant-bot/compare/v0.2.2...v0.2.3">
    <img src="https://img.shields.io/badge/Сравнить-v0.2.2...v0.2.3-blue?style=flat-square" alt="Compare">
  </a>
  <a href="https://github.com/bivlked/target-assistant-bot/releases/tag/v0.2.3">
    <img src="https://img.shields.io/badge/Релиз-v0.2.3-green?style=flat-square" alt="Release">
  </a>
</div>

### 🚀 Добавлено
- **Code Audit Stage 1** ✅ - Comprehensive code audit для повышения качества и надежности кода
- **Test Suite Update Stage 2** ✅ - Полное обновление всех тестов для multi-goal архитектуры
- **Достигнуто покрытие тестами 97.55%** 🎯 (199/204 тестов проходят)
- Улучшенная обработка ошибок во всех модулях
- Расширенная проверка актуальности библиотек и зависимостей

### 🛠️ Изменено
- **Матрица тестирования CI/CD**: Исключен Python 3.10 из-за несовместимости со Sphinx 8.2+
- **Требования Python**: Обновлены до 3.11+ во всей документации
- **Конфигурация pytest**: Добавлен pytest.ini с правильными настройками asyncio
- Оптимизирована логика работы с множественными целями
- Улучшена производительность операций с Google Sheets
- Усовершенствована работа с LLM API для более надежного парсинга ответов

### 🐛 Исправлено
- **Критические тесты планировщика** - исправлены для multi-goal архитектуры
- **Тесты async_fix** - исправлены сигнатуры функций
- **Тесты common_handlers** - обновлены тексты и flow
- **Тесты sheets_manager** - использование объектов Goal и новых сигнатур
- **Тесты async_sheets_manager** - правильные типы данных
- **Тесты goal_manager_async** - полная реализация DummyAsyncStorage
- **MyPy ошибки** - исправлены в test_sheets_extended_statistics.py
- Устранены все предупреждения pytest-asyncio
- Исправлены проблемы с покрытием кода в CI/CD
- Устранены потенциальные race conditions в асинхронном коде

### 📚 Документация (Stage 3)
- **Полностью переработан README.md** - современный дизайн с бейджами, диаграммами и эмодзи
- **Создан FAQ.md** - ответы на частые вопросы
- **Создан examples.md** - примеры и шаблоны целей
- **Создан google_sheets_setup.md** - подробная инструкция по настройке
- **Обновлен README_EN.md** - синхронизирован с русской версией
- Актуализированы инструкции по установке и развертыванию
- Удалены устаревшие файлы документации

### 🔧 Технические улучшения
- Полный аудит кода на соответствие современным best practices
- Проверка и обновление всех зависимостей до актуальных версий
- Оптимизация импортов и удаление неиспользуемого кода
- Улучшение типизации для лучшей поддержки MyPy

### 📂 Структура
- Перемещен `SENTRY_INTEGRATION_DEBUG_LOG.md` в папку `docs/`
- Удален устаревший файл `release_notes_v0.2.2.md`

## [Unreleased]

### 🚀 Добавлено
- Система категорий целей (по умолчанию: "Без категории").
- Отметки о важности целей.
- Отчеты по дням недели и месяцам.
- Экспорт данных в JSON.
- Архивирование выполненных целей.

### 🛠️ Изменено
- Улучшена производительность обработки больших объемов данных.
- Переработан интерфейс настроек уведомлений.

### 🐛 Исправлено
- Исправлена проблема с дублированием записей при синхронизации.
- Устранены ошибки отображения emoji в некоторых версиях Telegram.

## [0.2.2] - 2025-05-30

### 🔧 Рефакторинг кода (Code Audit v0.2.2)

#### Структурированное логирование
- **Исправлено 18 f-строк в логировании**: Заменены все f-string в логировании на структурированное логирование с `structlog`
- **Затронутые файлы**:
  - `sheets/client.py`
  - `main.py` 
  - `handlers/goal_setting.py`
  - `handlers/task_management.py`
  - `handlers/goals.py`
  - `core/goal_manager.py`
  - `llm/async_client.py`
  - `utils/subscription.py`
- **Миграция на structlog.get_logger**: Переход от `logging.getLogger` к `structlog.get_logger` где необходимо

#### Очистка кода
- **Удалены отладочные print-выражения**: Удалены 2 debug print из `core/goal_manager.py`
- **Очищены комментарии**: Удалены старые комментарии tenacity imports и неиспользуемые RETRY decorator комментарии
- **Исправлены устаревшие комментарии**: Обновлены или удалены 5+ устаревших комментариев
- **Переведены комментарии**: Все комментарии в коде переведены на английский язык (UI строки остались на русском)

#### Исправления интерфейсов
- **Обновлен AsyncStorageInterface**: Исправлено использование в `core/goal_manager.py`:
  - `clear_user_data` → `archive_goal` для всех активных целей
  - `save_goal_info` + `save_plan` → `save_goal_and_plan`
  - `get_task_for_date` → `get_task_for_today`
  - `update_task_status` → `update_task_status_old`
  - `get_statistics` → `get_status_message`
  - `get_extended_statistics` → оставлен как есть (legacy метод)
- **Исправлен формат пакетного обновления**: Конвертирован dict формат для совместимости с новым интерфейсом

#### Улучшения обработки ошибок
- **Консистентные сообщения об ошибках**: Улучшена согласованность сообщений об ошибках
- **Добавлен суффикс "Try later"**: Добавлен к сообщениям об ошибках где необходимо

#### Управление версиями
- **Исправлена резервная версия**: Изменена на "0.2.2" вместо generic "unknown"

#### Форматирование кода
- **Применен Black formatter**: Обеспечено прохождение всех файлов через Black formatting checks
- **Исправлен порядок импортов**: Убеждены что `from __future__ import annotations` первый где необходимо

### 🚨 Совместимость Python (Критическое изменение)
- **BREAKING CHANGE**: Исключена поддержка Python 3.10
- **Причина**: Sphinx 8.2+ требует Python ≥3.11 для сборки документации
- **Поддерживаемые версии**: Python 3.11, 3.12
- **Обновлены конфигурации**: pyproject.toml, CI/CD workflows, инструменты разработки

### 🚨 Оставшиеся задачи

#### GitHub Actions Deploy Error
- **Проблема**: Deploy workflow завершается с ошибкой "Error: missing server host"
- **Причина**: Отсутствующие GitHub secrets (PROD_HOST, PROD_USER, PROD_SSH_KEY, PROD_PORT)
- **Воздействие**: Низкое - ручной деплой все еще возможен
- **Рекомендация**: Добавить необходимые secrets в настройки GitHub репозитория

#### TODO комментарии
- **Найдено 6 TODO комментариев** в тестовых файлах (не критично):
  - `tests/test_sheets_manager.py`: 1 TODO
  - `tests/test_retry_decorators.py`: 3 TODOs
  - `tests/test_async_sheets_manager.py`: 2 TODOs
  - `tests/test_async_llm_client.py`: 2 TODOs

#### MyPy предупреждения
- Некоторые предупреждения MyPy type checking остались из-за эволюции интерфейсов
- Не критичны и могут быть исправлены в будущем рефакторинге

### 📊 Проверенные версии библиотек

#### Верифицированные библиотеки
- **python-telegram-bot**: v22.0+ (текущая, поддерживает async)
- **APScheduler**: v3.11.0 (текущая, < 4.0.0 как требуется)
- **OpenAI**: v1.82+ (текущая)
- **gspread**: v6.1.4+ (текущая)

#### Рекомендации
- Все основные библиотеки актуальны
- Срочные обновления не требуются

### 📈 Метрики качества кода

#### До аудита
- F-string logging экземпляры: 18
- Debug print выражения: 2
- Русские комментарии: 3
- Устаревшие комментарии: 5+

#### После аудита
- F-string logging экземпляры: 0 ✅
- Debug print выражения: 0 ✅
- Русские комментарии: 0 (кроме UI строк) ✅
- Устаревшие комментарии: 0 ✅

### 📋 Следующие шаги
1. **Merge branch**: Push и создание PR для `refactor/pre-release-0.2.2-audit`
2. **Обновление тестов**: Проверка и обновление тестов для новых интерфейсов
3. **Обновление документации**: Убеждение что вся документация отражает текущий код
4. **Release v0.2.2**: Создание и публикация релиза

### 🎯 Готовность к релизу
Кодовая база теперь более чистая, консистентная и следует лучшим практикам. Все критические вопросы были решены. Бот готов к релизу v0.2.2.

## [0.2.0] - 2025-01-17

### 🚀 Добавлено
- **Поддержка множественных целей**: теперь пользователи могут создавать до 10 активных целей одновременно
- **Новые модели данных**: Goal, Task, GoalStatistics с поддержкой приоритетов и тегов
- **Dependency Injection контейнер** для управления зависимостями
- **Новые команды**:
  - `/my_goals` - управление всеми целями
  - Интерактивные кнопки для создания и редактирования целей
- **Улучшенная архитектура**: полный переход на AsyncStorageInterface и AsyncLLMInterface
- **Система приоритетов**: высокий, средний, низкий приоритет для целей
- **Теги для целей**: возможность добавления тегов для лучшей организации
- **Расширенная статистика**: детальная аналитика по каждой цели и общая статистика
- **Модуль подписок**: управление подписками пользователей (in-memory)

### 🔧 Изменено
- **Полный рефакторинг архитектуры**: отказ от GoalManager в пользу dependency injection
- **Обновлены все handlers**: поддержка множественных целей во всех командах
- **Scheduler**: адаптирован для работы с множественными целями
- **SheetsManager**: добавлена поддержка нескольких листов для каждой цели
- **Улучшенный интерфейс**: новые inline-кнопки и интерактивные меню
- **Команда /today**: теперь показывает все задачи на день
- **Команда /status**: общая статистика по всем целям
- **Команда /check**: выбор конкретной цели для обновления статуса

### 📦 Технические улучшения
- Новая структура моделей данных в `core/models.py`
- Обновленные интерфейсы в `core/interfaces.py`
- Dependency injection в `core/dependency_injection.py`
- Новые обработчики в `handlers/goals.py`
- Обновленные тесты для множественных целей
- Миграция существующих данных в новый формат

### 🔄 Обратная совместимость
- Сохранена команда `/setgoal` для совместимости
- Автоматическая миграция существующих целей в новый формат
- Legacy методы в SheetsManager для поддержки старого API

## [0.1.1] - 2025-01-17

### 🐛 Исправлено
- Критический баг с event loops между PTB, APScheduler и AsyncSheetsManager
- Проблемы с `RuntimeError: Task got Future attached to a different loop`
- Улучшена обработка event loop в основном приложении

### 🔧 Изменено
- Рефакторинг `main.py` для использования `asyncio.run(main_async())`
- Обновлен `scheduler/tasks.py` для работы с переданным event loop
- Исправлен `sheets/async_client.py` для корректного получения текущего loop

### 📦 Добавлено
- Тесты для проверки исправления event loop (`tests/test_async_fix.py`)
- Улучшенное логирование для отслеживания проблем с event loop

## [0.1.0] - 2025-01-16

### 🎉 Первый релиз
- Первый стабильный релиз с полной асинхронной архитектурой
- Docker образы публикуются в GitHub Container Registry
- Высокое покрытие тестами (~99%)
- Полная документация на русском и английском языках

## [Старые версии]

### Major Refactoring & Enhancements
- **Full Asynchronous Architecture**: Migrated core components (`GoalManager`, `LLMClient`, `SheetsManager`) to fully asynchronous operations using `async/await`, `AsyncLLMClient`, and `AsyncSheetsManager`.
- **Dependency Injection**: Introduced `AsyncStorageInterface` and `AsyncLLMInterface` for improved flexibility and testability of `GoalManager`.
- **Test Suite Overhaul (Task #30)**:
  - Significantly increased test coverage across the project to ~99%.
  - Conducted a thorough review and refactoring of all existing test files.
  - Created new test suites for `handlers/common.py`, `utils/sentry_integration.py`, `utils/retry_decorators.py`, and `sheets/async_client.py`.
  - Improved mocking strategies, including the adoption of `freezegun` for time-sensitive tests and `pytest-asyncio` for async fixtures.
  - Addressed and resolved numerous issues identified by `mypy` and improved type hinting.
- **API Documentation**:
  - Integrated Sphinx for automatic API documentation generation from docstrings.
  - Set up GitHub Actions workflow to build and publish Sphinx documentation to GitHub Pages.
  - Updated `README.md` with instructions for local documentation generation.
- **CI/CD and Release Process**:
  - Enhanced `deploy/update-bot.sh` script to support deployments based on Git tags for releases.
  - Configured Docker CI workflow (`docker.yml`) to build and publish Docker images to GitHub Container Registry (GHCR) upon new tag/release creation.

### Changed
- **Code Quality**:
  - Systematically translated a significant portion of comments and docstrings to English.
  - Resolved various pre-commit hook issues, particularly with `detect-secrets` and `mypy`.
  - Standardized error handling for LLM and Sheets API calls using custom retry decorators.
- **LLM Interaction**: Improved robustness of `_extract_plan` in `AsyncLLMClient` for parsing LLM responses.
- **Dependencies**: Added `freezegun` and `types-requests` to development/test dependencies.

### Removed
- **Synchronous Clients**: Removed legacy synchronous `llm/client.py` (and its tests) and refactored `sheets/client.py` to be primarily used by `AsyncSheetsManager`.
- **Redundant Test Files**: Consolidated tests for `period_parser`, removing duplicate test files (`test_period_parser_extra.py`, `test_period_parser_additional.py`).
- **Redundant `test_sheets.py`**: Merged its relevant tests into `test_sheets_manager.py`.

### Fixed
- Corrected error in `period_parser` heuristic and LLM fallback logic.
- Resolved multiple issues in tests related to mocking, asynchronous operations, and date/time handling.

### Added
- Configurable Prometheus metrics port via `PROMETHEUS_PORT` environment variable
- Script for dependency analysis (`scripts/analyze_dependencies.py`)
- Automatic version detection from `pyproject.toml`

### Changed
- Updated dependencies to latest stable versions:
  - `openai` >=1.82
  - `gspread` >=6.1.4
  - `tenacity` >=9.1
  - `structlog` >=25.3
  - `prometheus-client` >=0.21
  - `sentry-sdk` >=2.29

### Fixed
- Removed 66 unused imports across the codebase
- Fixed compatibility with Python 3.10 for reading `pyproject.toml`

### Removed
- Commented out legacy code in `scheduler/tasks.py`
- Unnecessary TODO comments that were already addressed

## 1.2 — 2025-05-05

### Added
- Миграция планировщика на `AsyncIOScheduler` (асинхронный режим по умолчанию).
- Матрица тестов GitHub-Actions для Python 3.10–3.12 (`tests.yml`).
- Отчёт о покрытии кода публикуется в Codecov.
- Заглушки `google_credentials.json` и fallback-файл для стабильного CI.
- Бейджи `Tests` и актуальные версии Python в README.

### Changed
- `GoogleConfig` больше не `frozen=True` — позволяет monkeypatch в тестах.
- README: уточнены названия листов, пути запуска, обновлены ссылки.
- Тесты `SheetsManager` расширены, фиктивные файлы создаются через `conftest.py`.
- Удалена зависимость `six`; APScheduler зафиксирован на 3.11.

### Removed
- Удалена устаревшая ветка `chore/update-changelog-1.1` из origin.

## 1.1 — 2025-05-02

### Added
- Интеграция структурированного логгирования `structlog` и отправка ошибок в Sentry.
- CI-workflow GitHub Actions с прогоном тестов и линтера.
- Асинхронные клиенты Google Sheets и GoalManager (`set_new_goal_async`).
- Заглушка пути `google_credentials.json` в тестах для независимости окружения.

### Changed
- Расширены мок-классы `DummySpreadsheet` и `DummyWorksheet` для полного покрытия API.
- Исправлены smoke-тесты, обновлена проверка `auto_resize`.

### Docs
- README дополнен разделами Docker Compose и systemd.
- Обновлена архитектурная документация.

## 1.0 — initial release

### Added
- Базовый бот Telegram на python-telegram-bot 20.
- Диалог /setgoal с интеграцией OpenAI.
- Google Sheets хранение цели и плана.
- Планировщик напоминаний `apscheduler`.
- Команды: /start, /help, /today, /check, /status, /motivation, /reset.
- Автоматический setup_commands.py для BotFather.

### Changed
- Русифицированы подписи листа «Цель».
- Формат даты – dd.mm.yyyy.

### Removed
- Удалены старые каталоги OLD/ и AnotherCrewCode/.

### Docs
- README, install_ubuntu, architecture, user_guide.

<div align="center">
  <p>
    <strong>🚀 Полная история релизов</strong><br>
    <a href="https://github.com/bivlked/target-assistant-bot/releases">Посмотреть все релизы на GitHub</a>
  </p>
</div>