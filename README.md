<h1 align="center">
  <img src=".github/assets/logo.svg" alt="Target Assistant Bot" width="200" height="200">
  <br>
  🎯 Target Assistant Bot
</h1>

<p align="center">
  <strong>Ваш персональный ассистент для достижения целей</strong>
</p>

<p align="center">
  <a href="README_EN.md">🌐 English</a> •
  <a href="#-возможности">✨ Возможности</a> •
  <a href="#-быстрый-старт">🚀 Быстрый старт</a> •
  <a href="#-документация-и-ресурсы">📚 Документация</a>
</p>

<p align="center">
  <a href="https://github.com/bivlked/target-assistant-bot/actions/workflows/ci.yml">
    <img src="https://github.com/bivlked/target-assistant-bot/actions/workflows/ci.yml/badge.svg" alt="CI/CD Pipeline">
  </a>
  <a href="https://github.com/bivlked/target-assistant-bot/actions/workflows/tests.yml">
    <img src="https://github.com/bivlked/target-assistant-bot/actions/workflows/tests.yml/badge.svg" alt="Tests & Coverage">
  </a>
  <a href="https://codecov.io/gh/bivlked/target-assistant-bot">
    <img src="https://codecov.io/gh/bivlked/target-assistant-bot/branch/main/graph/badge.svg" alt="Coverage Status">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python Version">
  </a>
</p>

<p align="center">
  <a href="https://github.com/psf/black">
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black">
  </a>
  <a href="https://conventionalcommits.org">
    <img src="https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white" alt="Conventional Commits">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT">
  </a>
  <a href="https://github.com/bivlked/target-assistant-bot/releases/latest">
    <img src="https://img.shields.io/github/v/release/bivlked/target-assistant-bot.svg" alt="GitHub Release">
  </a>
</p>

---

Персональный Telegram-бот-ассистент, который помогает формулировать цели, разбивать их на ежедневные задачи и отслеживать прогресс с сохранением в Google Sheets. **Теперь с поддержкой до 10 одновременных целей!**

<div align="center">
  <table>
    <tr>
      <td align="center"><strong>🚀 Цель проекта</strong></td>
      <td>Создать умного и отзывчивого помощника для эффективного движения к долгосрочным целям</td>
    </tr>
    <tr>
      <td align="center"><strong>🎯 Ключевые технологии</strong></td>
      <td>Python • python-telegram-bot • OpenAI API • Google Sheets API</td>
    </tr>
    <tr>
      <td align="center"><strong>📊 Статус</strong></td>
      <td>v0.2.3 - Production Ready с мульти-целями</td>
    </tr>
    <tr>
      <td align="center"><strong>📄 Презентация</strong></td>
      <td><a href="Персональный%20ассистент%20для%20помощи%20в%20достижении%20поставленных%20целей.pdf">Полная презентация проекта (PDF, RU)</a></td>
    </tr>
  </table>
</div>

---

## ✨ Новые возможности в v0.2.0

### 🎯 Множественные цели
- **До 10 активных целей одновременно** - больше никаких ограничений одной целью
- **Приоритеты** - высокий 🔴, средний 🟡, низкий 🟢 для лучшей организации
- **Теги** - группируйте цели по категориям (работа, здоровье, саморазвитие)
- **Статусы** - активные, завершенные, архивированные цели

### 📊 Улучшенная аналитика
- **Общая статистика** по всем целям с прогрессом
- **Детальная аналитика** для каждой цели отдельно
- **Отслеживание** дней до завершения и темпа выполнения

### 🎮 Интерактивный интерфейс
- **Inline-кнопки** для быстрых действий
- **Wizard создания целей** с пошаговым руководством
- **Управление целями** через удобные меню

## 💡 Примеры использования

### 🌟 Новый сценарий: Управление множественными целями

Представьте, что у вас есть несколько целей:
1. "Изучить Python за 3 месяца" (🔴 высокий приоритет)
2. "Пробежать полумарафон" (🟡 средний приоритет) 
3. "Прочитать 20 книг за год" (🟢 низкий приоритет)

**Создание первой цели:**
1. **Вы**: `/start`
   **Бот**: 🎯 Добро пожаловать в Target Assistant Bot! Я помогу вам управлять до 10 целями одновременно...
2. **Вы**: `/my_goals`
   **Бот**: 📝 У вас пока нет целей. Используйте /add_goal для создания новой цели.
3. **Вы**: Нажимаете кнопку "➕ Добавить цель"
   **Бот**: 🎯 Создание новой цели. Шаг 1/6: Введите короткое название цели...

**Управление несколькими целями:**
4. **Вы**: `/today`
   **Бот**: 📅 Задачи на сегодня:
   🔴 **Изучение Python**: Освоить основы ООП в Python
   🟡 **Полумарафон**: Пробежать 5 км в медленном темпе
   🟢 **Чтение книг**: Прочитать 30 страниц "Чистый код"

5. **Вы**: `/status`
   **Бот**: 📊 Общий статус целей:
   • Всего целей: 3
   • Активных: 3
   • Общий прогресс: 35%
   
   🎯 Активные цели:
   🔴 **Изучение Python** - 45% • 📅 15.04.2025
   🟡 **Полумарафон** - 30% • 📅 01.05.2025
   🟢 **Чтение книг** - 25% • 📅 31.12.2025

### ☀️ Новое ежедневное взаимодействие

**Утреннее напоминание (автоматическое):**
**Бот**: ☀️ Доброе утро! Ваши задачи на сегодня:
• **Изучение Python**: Создать первый класс в Python
• **Полумарафон**: Легкая пробежка 3 км

[📝 Отметить выполнение] [📊 Общий статус]

**Быстрая отметка выполнения:**
**Вы**: Нажимаете "📝 Отметить выполнение"
**Бот**: 📝 Выберите задачу для обновления статуса:
- Изучение Python: Создать первый класс...
- Полумарафон: Легкая пробежка 3 км

---

## 🛠️ Возможности

### Основные команды

| Команда | Описание |
|---------|----------|
| `/start` | 🚀 Начать работу с ботом |
| `/help`  | ℹ️ Справка по доступным командам |
| `/my_goals` | 🎯 **[НОВОЕ]** Управление всеми целями - главная команда |
| `/add_goal` | ➕ **[НОВОЕ]** Создать новую цель через интерактивный интерфейс |
| `/setgoal` | 🎯 Создать цель через текстовый диалог (legacy) |
| `/today` | 📅 **[ОБНОВЛЕНО]** Все задачи на сегодня из всех активных целей |
| `/check` | ✍️ **[ОБНОВЛЕНО]** Отметить выполнение с выбором конкретной цели |
| `/status` | 📊 **[ОБНОВЛЕНО]** Общий прогресс по всем целям |
| `/motivation` | 💡 **[ОБНОВЛЕНО]** Мотивация на основе всех ваших целей |
| `/cancel` | ⛔ Отменить текущую операцию |
| `/reset` | 🗑️ Сбросить все цели (удалить данные полностью) |

### Новые возможности

- **🎯 До 10 одновременных целей** - работайте над несколькими направлениями
- **📊 Приоритеты** - высокий (🔴), средний (🟡), низкий (🟢)
- **🏷️ Теги** - организуйте цели по категориям
- **📋 Интерактивное управление** - кнопки для всех действий
- **📈 Расширенная статистика** - детальная аналитика по каждой цели
- **🔄 Автомиграция** - существующие цели автоматически переносятся в новый формат

### Структура хранения данных

Бот создает индивидуальную Google-таблицу с улучшенной структурой:
* **"Список целей"** — главный лист со всеми вашими целями, их статусами и прогрессом
* **"Цель 1", "Цель 2", ..., "Цель 10"** — отдельные листы с планами для каждой цели
* **Автоматическая миграция** — существующие данные переносятся в новый формат

## 📋 Требования

<div align="center">

| Компонент | Версия | Примечание |
|-----------|--------|-----------|
| 🐍 Python | 3.11+ | Рекомендуется 3.11-3.12 |
| 🤖 Telegram Bot Token | - | [Получить у @BotFather](https://t.me/BotFather) |
| 🔑 OpenAI API Key | - | [Получить на OpenAI](https://platform.openai.com/api-keys) |
| 📊 Google Service Account | - | [Инструкция в документации](docs/install_ubuntu.md#создание-google-service-account) |

</div>

## 🚀 Быстрый старт (локально с `venv`)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# переменные окружения
cp .env.example .env
$EDITOR .env  # поставить TELEGRAM_BOT_TOKEN и GOOGLE_CREDENTIALS_PATH

python main.py
```

## 🐳 Быстрый старт (Docker Compose)

```bash
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
cp .env.example .env
# Отредактируйте .env, затем:
docker compose up -d --build
```

## ☁️ Деплой на сервер (systemd)

1. Клонируйте репозиторий и установите окружение:

```bash
sudo apt update && sudo apt install -y python3 python3-venv git
sudo useradd -m targetbot
sudo -iu targetbot

# клонируем бот
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

2. Скопируйте ваши `google_credentials.json` и заполните `.env` (можно взять шаблон `env.example`).

3. Скопируйте unit-файл и перезапустите службу:

```bash
sudo cp deploy/targetbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now targetbot.service
```

4. (Опционально) Установите автo-обновление:

```bash
sudo cp deploy/update-bot.sh /usr/local/bin/update-bot.sh
# This script will now pull the latest release tag by default.
# Check for updates e.g., every 15 minutes
echo "*/15 * * * * root /usr/local/bin/update-bot.sh >> /var/log/targetbot_update.log 2>&1" | sudo tee /etc/cron.d/targetbot-update
```

## 📚 Документация и ресурсы

* [Руководство пользователя](docs/user_guide.md)
* [Установка на Ubuntu (краткая)](docs/install_ubuntu.md)
* [Установка на Ubuntu (подробная)](docs/install_ubuntu_detailed.md)
* [Архитектура проекта](docs/architecture.md)
* [Список изменений](CHANGELOG.md)

Для разработчиков:
* [Руководство по участию (CONTRIBUTING.md)](CONTRIBUTING.md)
* [Чек-лист разработки (актуальные задачи)](DEVELOPMENT_CHECKLIST.md)

---

## 📖 Сборка API Документации (Sphinx)

API документация проекта генерируется из docstrings с помощью [Sphinx](https://www.sphinx-doc.org/).

**Для локальной сборки документации:**

1.  Убедитесь, что вы находитесь в активированном виртуальном окружении с установленными зависимостями (включая те, что в секции `# --- Documentation ---` файла `requirements.txt`).
2.  Перейдите в директорию `docs/`:
    ```bash
    cd docs
    ```
3.  Выполните команду сборки:
    *   Для Linux/macOS/Git Bash:
        ```bash
        make html
        ```
    *   Для Windows (CMD/PowerShell):
        ```bash
        .\make.bat html
        ```
4.  Сгенерированная документация будет доступна в директории `docs/build/html/`. Откройте файл `index.html` в вашем браузере.

---

## 📜 Лицензия

Проект распространяется по лицензии MIT. Подробности в файле [LICENSE](LICENSE).

---

<div align="center">

### 🌟 Поддержать проект

Если проект оказался полезным, вы можете:

[![Star on GitHub](https://img.shields.io/github/stars/bivlked/target-assistant-bot.svg?style=social)](https://github.com/bivlked/target-assistant-bot/stargazers)
[![Fork on GitHub](https://img.shields.io/github/forks/bivlked/target-assistant-bot.svg?style=social)](https://github.com/bivlked/target-assistant-bot/network/members)
[![Watch on GitHub](https://img.shields.io/github/watchers/bivlked/target-assistant-bot.svg?style=social)](https://github.com/bivlked/target-assistant-bot/watchers)

<br>

**Made with ❤️ by [bivlked](https://github.com/bivlked)**

<sub>Есть вопросы? Создайте [Issue](https://github.com/bivlked/target-assistant-bot/issues/new/choose) или напишите в [Discussions](https://github.com/bivlked/target-assistant-bot/discussions)</sub>

</div>

## 🎯 Roadmap

### ✅ v0.2.0 - Multi-Goals (Текущий релиз)
- ✅ Поддержка до 10 одновременных целей
- ✅ Приоритеты и теги для целей
- ✅ Интерактивный UI с inline-кнопками
- ✅ Расширенная статистика и аналитика
- ✅ Полная обратная совместимость

### 🔮 v0.3.0 - Advanced Analytics (Планируется)
- 📊 Графики прогресса и визуализация
- 📈 Экспорт статистики в PDF
- 🔍 Сравнение целей между собой
- 🎨 Улучшенный UI с прогресс-барами

### 🚀 v1.0.0 - Integration & Gamification
- 📅 Интеграция с Google Calendar
- 🏆 Система достижений и наград
- 🌐 REST API для внешних интеграций
- 📱 Мобильное веб-приложение
