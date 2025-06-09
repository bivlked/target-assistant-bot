# 🏗️ Архитектура проекта Target Assistant Bot

<p align="center">
  <strong>Высокоуровневая архитектура и взаимодействие компонентов</strong>
</p>

## 📊 Диаграмма архитектуры

```mermaid
graph TD
    A[Telegram Bot API] -->|Webhook/LongPoll| B(main.py)
    B --> C[handlers/*]
    C --> D[core/goal_manager.py]
    D --> IF_Storage(StorageInterface)
    D --> IF_LLM(LLMInterface)
    IF_Storage <.. sheets_sync[sheets/client.py : SheetsManager]
    IF_Storage <.. sheets_async[sheets/async_client.py : AsyncSheetsManager]
    IF_LLM <.. llm_sync[llm/client.py : LLMClient]
    IF_LLM <.. llm_async[llm/async_client.py : AsyncLLMClient]
    sheets_sync --> cache[utils/cache.py : SheetCache]
    D -.-> rl[utils/ratelimiter.py : UserRateLimiter] -.-> F
    B --> G[scheduler/tasks.py]
    G -->|async| D
    B --> metrics_http[Prometheus HTTP /metrics]
    subgraph Core Logic
        D
        G
        M[core/metrics.py]
        IF_Storage
        IF_LLM
    end
    subgraph Внешние сервисы
        H[Google Sheets API]
        I[OpenAI API]
    end
    sheets_sync <-->|gspread| H
    llm_sync <-->|HTTP| I
    metrics_http -.-> M
    D -.-> M
    sheets_sync -.-> M
    llm_sync -.-> M
```

## 🧱 Основные компоненты и модули

| Каталог | Назначение |
|---------|------------|
| `main.py` | Точка входа, инициализация зависимостей и Telegram-бота |
| `handlers/` | Telegram-команды и диалоги (PTB 20) |
| `core/goal_manager.py` | Бизнес-логика: постановка цели, получение задач, мотивации |
| `core/interfaces.py` | Абстрактные интерфейсы (Протоколы) для Storage и LLM, обеспечивающие DI. |
| `core/metrics.py` | Определения метрик Prometheus для мониторинга приложения. |
| `sheets/client.py` | Синхронный клиент для работы с Google Sheets (`gspread`). Реализует `StorageInterface`. |
| `sheets/async_client.py` | Асинхронная обертка над `SheetsManager`. Реализует `AsyncStorageInterface`. |
| `llm/client.py` | Синхронный клиент для работы с OpenAI API. Реализует `LLMInterface`. |
| `llm/async_client.py` | Асинхронная обертка над `LLMClient`. Реализует `AsyncLLMInterface`. |
| `scheduler/` | Фоновые напоминания `AsyncIOScheduler` (утро/вечер, мотивация) |
| `utils/` | Вспомогательные утилиты: форматирование дат, парсинг периода, кэширование (`SheetCache`), ограничение частоты запросов (`UserRateLimiter`), декораторы retry. |

## 🔄 Поток данных (упрощенно)
1. Пользователь отправляет `/setgoal` → диалог (`handlers/`) запрашивает параметры.
2. `GoalManager` проверяет лимит запросов к LLM (`UserRateLimiter`).
3. `GoalManager.set_new_goal` генерирует план через `LLMInterface`, затем сохраняет цель и план через `StorageInterface` (создается/обновляется Google-таблица).
4. `/today` или планировщик (`scheduler/`) извлекают задачу на текущий день через `GoalManager` (который использует `StorageInterface` с возможным кэшированием через `SheetCache`).
5. `/check` обновляет статус задачи в таблице через `GoalManager` и `StorageInterface` (кэш для этой операции инвалидируется).
6. Различные компоненты обновляют метрики в `core/metrics.py`, которые доступны через HTTP эндпоинт, запущенный в `main.py`.

## 🔗 Внешние зависимости и окружение
* Python 3.12+
* Google Service Account JSON (путь указывается в `GOOGLE_CREDENTIALS_PATH`)
* OpenAI API key (указывается в `OPENAI_API_KEY`)
* Используются абстрактные интерфейсы для Dependency Injection (DI); реализован простой DI-контейнер в `core/dependency_injection.py`.

Сеть должна быть доступна к `api.telegram.org`, `sheets.googleapis.com`, `api.openai.com`. 