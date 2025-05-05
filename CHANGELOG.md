# Changelog

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