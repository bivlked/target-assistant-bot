# 🏗️ Архитектура проекта Target Assistant Bot

Данный документ описывает основные компоненты и их взаимодействие в боте.

```mermaid
graph TD
    A[Telegram Bot API] -->|Webhook/LongPoll| B(main.py)
    B --> C[handlers/*]
    C --> D[core/goal_manager.py]
    D --> IF_Storage(AsyncStorageInterface)
    D --> IF_LLM(AsyncLLMInterface)
    
    subgraph "Storage Layer"
        IF_Storage <.. sheets_async[sheets/async_client.py : AsyncSheetsManager]
        sheets_async --> sheets_sync_internal[sheets/client.py : SheetsManager (Sync Core)]
        sheets_sync_internal --> cache[utils/cache.py : SheetCache]
        sheets_sync_internal <-->|gspread| H[Google Sheets API]
    end

    subgraph "LLM Layer"
        IF_LLM <.. llm_async[llm/async_client.py : AsyncLLMClient]
        llm_async <-->|openai lib| I[OpenAI API]
    end
    
    D -.-> rl[utils/ratelimiter.py : UserRateLimiter] 
    B --> G[scheduler/tasks.py]
    G -->|async| D
    
    subgraph "Monitoring & Core Utils"
        B --> metrics_http[Prometheus HTTP /metrics]
        metrics_http -.-> M[core/metrics.py]
        D -.-> M
        sheets_async -.-> M
        llm_async -.-> M
        rl
        cache
    end
    
    subgraph "External Services"
      H
      I
    end
```

## 🧱 Основные компоненты и модули

| Каталог | Назначение |
|---------|------------|
| `main.py` | Точка входа, инициализация зависимостей и Telegram-бота |
| `handlers/` | Telegram-команды и диалоги (PTB 20) |
| `core/goal_manager.py` | Бизнес-логика: постановка цели, получение задач, мотивации (полностью асинхронный) |
| `core/interfaces.py` | Абстрактные интерфейсы (Протоколы) для `AsyncStorageInterface` и `AsyncLLMInterface`, обеспечивающие DI. |
| `core/metrics.py` | Определения метрик Prometheus для мониторинга приложения. |
| `sheets/client.py` | Синхронная реализация логики для Google Sheets (`gspread`). Используется внутри `AsyncSheetsManager`. |
| `sheets/async_client.py` | Асинхронный клиент для работы с Google Sheets. Реализует `AsyncStorageInterface`, оборачивая вызовы к синхронному `sheets.client`. |
| `llm/async_client.py` | Асинхронный клиент для работы с OpenAI API. Реализует `AsyncLLMInterface`. |
| `scheduler/` | Фоновые напоминания `AsyncIOScheduler` (утро/вечер, мотивация) |
| `utils/` | Вспомогательные утилиты: форматирование дат, парсинг периода, кэширование (`SheetCache`), ограничение частоты запросов (`UserRateLimiter`), декораторы retry. |

## 🔄 Поток данных (упрощенно)
1. Пользователь отправляет `/setgoal` → диалог (`handlers/`) запрашивает параметры.
2. `GoalManager` проверяет лимит запросов к LLM (`UserRateLimiter`).
3. `GoalManager.set_new_goal` (асинхронный) генерирует план через `AsyncLLMInterface`, затем сохраняет цель и план через `AsyncStorageInterface`.
4. `/today` или планировщик (`scheduler/`) извлекают задачу на текущий день через `GoalManager` (который использует `AsyncStorageInterface` с возможным кэшированием).
5. `/check` обновляет статус задачи в таблице через `GoalManager` и `AsyncStorageInterface` (кэш для этой операции инвалидируется).
6. Различные компоненты обновляют метрики в `core/metrics.py`, которые доступны через HTTP эндпоинт, запущенный в `main.py`.

## 🔗 Внешние зависимости и окружение
* Python 3.10–3.12
* Google Service Account JSON (путь указывается в `GOOGLE_CREDENTIALS_PATH`)
* OpenAI API key (указывается в `OPENAI_API_KEY`)
* Используются абстрактные интерфейсы для Dependency Injection (DI); конкретный DI-контейнер пока не применяется.

Сеть должна быть доступна к `api.telegram.org`, `sheets.googleapis.com`, `api.openai.com`. 