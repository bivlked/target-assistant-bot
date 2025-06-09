.. Target Assistant Bot documentation master file

====================================
🎯 Target Assistant Bot Documentation
====================================

.. image:: https://github.com/bivlked/target-assistant-bot/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/bivlked/target-assistant-bot/actions/workflows/ci.yml
   :alt: CI/CD Pipeline

.. image:: https://codecov.io/gh/bivlked/target-assistant-bot/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/bivlked/target-assistant-bot
   :alt: Coverage Status

.. image:: https://img.shields.io/badge/python-3.12%2B-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python Version

**Версия**: v0.2.4 | **Лицензия**: MIT | **GitHub**: `bivlked/target-assistant-bot <https://github.com/bivlked/target-assistant-bot>`_

---

📋 Содержание
=============

.. toctree::
   :maxdepth: 2
   :caption: Начало работы

   getting_started
   installation
   configuration

.. toctree::
   :maxdepth: 2
   :caption: Руководство пользователя

   user_guide
   commands
   faq

.. toctree::
   :maxdepth: 2
   :caption: Для разработчиков

   architecture
   contributing
   api_reference

.. toctree::
   :maxdepth: 2
   :caption: API документация

   api/main
   api/config
   api/core
   api/handlers
   api/scheduler
   api/sheets
   api/llm
   api/utils

🚀 О проекте
============

**Target Assistant Bot** — это персональный Telegram-ассистент, который помогает:

* 🎯 Формулировать четкие цели
* 📅 Разбивать их на ежедневные задачи
* 📊 Отслеживать прогресс достижения
* 💪 Поддерживать мотивацию

Все данные хранятся в **Google Sheets**, а планирование и мотивационные сообщения генерируются с помощью **OpenAI GPT-4**.

✨ Ключевые возможности
======================

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Команда
     - Описание
   * - ``/start``
     - 🚀 Начать работу с ботом
   * - ``/help``
     - ℹ️ Справка по доступным командам
   * - ``/setgoal``
     - 🎯 Установить новую цель
   * - ``/today``
     - 📅 Задача на сегодня
   * - ``/check``
     - ✍️ Отметить выполнение задачи
   * - ``/status``
     - 📊 Посмотреть прогресс
   * - ``/motivation``
     - 💡 Получить мотивацию
   * - ``/reset``
     - 🗑️ Сбросить все цели

🏗️ Архитектура
===============

Проект построен на современной асинхронной архитектуре:

* **Асинхронность**: Все компоненты работают через ``asyncio``
* **DI**: Dependency Injection через интерфейсы
* **Кэширование**: Google Sheets данные кэшируются в памяти
* **Rate Limiting**: Защита от превышения лимитов API
* **Мониторинг**: Prometheus метрики и Sentry для ошибок

📊 Статистика проекта
====================

* **Покрытие тестами**: 98.62% ✅
* **Поддерживаемые Python**: 3.12+ (рекомендуется 3.12)
* **Основные зависимости**:
  
  * ``python-telegram-bot`` 22.0
  * ``openai`` 1.77+
  * ``gspread`` 6.0.2
  * ``APScheduler`` 3.11.0

🔗 Полезные ссылки
==================

* `GitHub репозиторий <https://github.com/bivlked/target-assistant-bot>`_
* `Руководство по установке <https://github.com/bivlked/target-assistant-bot/blob/main/docs/install_ubuntu_detailed.md>`_
* `Чек-лист разработки <https://github.com/bivlked/target-assistant-bot/blob/main/DEVELOPMENT_CHECKLIST.md>`_
* `Issues и баг-репорты <https://github.com/bivlked/target-assistant-bot/issues>`_

📝 Индексы и таблицы
====================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

