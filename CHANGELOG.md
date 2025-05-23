# Changelog

## [Unreleased]

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

## 1.2 — 2025-05-05

### Added
* Миграция планировщика на `AsyncIOScheduler` (асинхронный режим по умолчанию).
* Матрица тестов GitHub-Actions для Python 3.10–3.12 (`tests.yml`).
* Отчёт о покрытии кода публикуется в Codecov.
* Заглушки `google_credentials.json` и fallback-файл для стабильного CI.
* Бейджи `Tests` и актуальные версии Python в README.

### Changed
* `GoogleConfig` больше не `frozen=True` — позволяет monkeypatch в тестах.
* README: уточнены названия листов, пути запуска, обновлены ссылки.
* Тесты `SheetsManager` расширены, фиктивные файлы создаются через `conftest.py`.
* Удалена зависимость `six`; APScheduler зафиксирован на 3.11.

### Removed
* Удалена устаревшая ветка `chore/update-changelog-1.1` из origin.

## 1.1 — 2025-05-02

### Added
* Интеграция структурированного логгирования `structlog` и отправка ошибок в Sentry.
* CI-workflow GitHub Actions с прогоном тестов и линтера.
* Асинхронные клиенты Google Sheets и GoalManager (`set_new_goal_async`).
* Заглушка пути `google_credentials.json` в тестах для независимости окружения.

### Changed
* Расширены мок-классы `DummySpreadsheet` и `DummyWorksheet` для полного покрытия API.
* Исправлены smoke-тесты, обновлена проверка `auto_resize`.

### Docs
* README дополнен разделами Docker Compose и systemd.
* Обновлена архитектурная документация.

## 1.0 — initial release

### Added
* Базовый бот Telegram на python-telegram-bot 20.
* Диалог /setgoal с интеграцией OpenAI.
* Google Sheets хранение цели и плана.
* Планировщик напоминаний `apscheduler`.
* Команды: /start, /help, /today, /check, /status, /motivation, /reset.
* Автоматический setup_commands.py для BotFather.

### Changed
* Русифицированы подписи листа «Цель».
* Формат даты – dd.mm.yyyy.

### Removed
* Удалены старые каталоги OLD/ и AnotherCrewCode/.

### Docs
* README, install_ubuntu, architecture, user_guide. 