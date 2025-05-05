# Changelog

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