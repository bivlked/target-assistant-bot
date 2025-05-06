# LOCAL DEV PLAN (private, не коммитить)

> Этот файл предназначен только для внутренней разработки и **не должен** публиковаться в публичном репозитории.
> Он исключён из Git с помощью правила `LOCAL_DEV_PLAN.md` в `.gitignore`.

## Принципы разработки (актуальная версия)

1. Сохраняем существующий пользовательский функционал; изменения не ломают API/UX.
2. Работает только асинхронный стек (`python-telegram-bot>=22`, `AsyncIOScheduler`).
3. Покрытие тестами ≥ 80 % (цель — 90 %). Любой PR не снижает coverage.
4. Стиль кода: `black`, `ruff`, `mypy`, Conventional Commits. Pre-commit обязателен.
5. CI должен быть «зелёным» (lint + тесты + coverage + placeholder-check).
6. В репозиторий не попадают плейсхолдеры/секреты. Используем файл `.env` и `detect-secrets`.

## Дорожная карта

| # | Этап | Статус |
|---|------|--------|
| 1 | Анализ проекта, составление плана | ✅ |
| 2 | Удаление дублирующей папки `schedulers/` | ✅ |
| 3 | Полная async-миграция (`GoalManager`, handlers, scheduler) | ✅ |
| 4 | Пакетное обновление статусов `batch_update_task_statuses` | ✅ |
| 5 | Pre-commit hook `forbid_placeholders` + CI-шаг | ✅ |
| 6 | Повышение покрытия до 80 % | ✅ |
| 7 | Чистка репо от плейсхолдеров, защита в CI | ✅ |
| 8 | Docker + Compose для prod | ✅ |
| 9 | Автодеплой (GitHub → server, версиями) | ⏳ |
|10 | Structured logging + Prometheus metrics | ⏳ |
|11 | DI container (`wired` or `punq`) | ⏳ |
|12 | API-документация (Sphinx + mkdocs) | ⏳ |
|13 | Dependabot / safety CI | ⏳ |
|14 | Raise coverage to 90 % | ⏳ |
|15 | Масштаб: поддержка до 20 пользователей / 10 целей каждый | ⏳ |
|16 | Кэширование и оптимизация LLM-запросов (модель, токены, батчинг) | ⏳ |

## Ближайшие задачи (спринт M05-W2)

- [x] Написать юнит-тесты для `SheetsManager.get_extended_statistics` и async-методов.
- [x] Добавить докстринги во все публичные методы core и sheets.
- [x] Подготовить Dockerfile и Github Actions для сборки образа.
- [x] Настроить workflow «deploy on tag» (ssh в prod-сервер + systemd restart).
- [ ] Проектировать многопользовательскую схему (ID пользователя → отдельный Spreadsheet / листы).
- [ ] Внедрить кэширование ответов LLM (LRU или Redis) и выбор дешёвой модели.

## Идеи из внешних рекомендаций

- [x] CONTRIBUTING.md + шаблоны Issue/PR (рекомендации-1, п.3).
- [x] LICENSE файл (рекомендации-1, п.2).
- [x] Dependabot + badges покрытия (рекомендации-1, п.6).
- [ ] DI container и разделение модулей Sheets/LLM (рекомендации-2, п.7).
- [ ] Мониторинг Prometheus + alerter (рекомендации-2, п.5).