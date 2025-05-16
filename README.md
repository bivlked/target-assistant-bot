<h1 align="center">🎯 Target Assistant Bot</h1>

*Read this in other languages: [English](README_EN.md)*

[![CI/CD Pipeline](https://github.com/bivlked/target-assistant-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/bivlked/target-assistant-bot/actions/workflows/ci.yml)
[![Tests & Coverage](https://github.com/bivlked/target-assistant-bot/actions/workflows/tests.yml/badge.svg)](https://github.com/bivlked/target-assistant-bot/actions/workflows/tests.yml)
[![Coverage Status](https://codecov.io/gh/bivlked/target-assistant-bot/branch/main/graph/badge.svg)](https://codecov.io/gh/bivlked/target-assistant-bot)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/bivlked/target-assistant-bot)](https://github.com/bivlked/target-assistant-bot/releases/latest)

Персональный Telegram-бот-ассистент, который помогает формулировать цели, разбивать их на ежедневные задачи и отслеживать прогресс с сохранением в Google Sheets.

> 🚀 **Цель проекта**: Создать умного и отзывчивого помощника для эффективного движения к долгосрочным целям.
> 🎯 **Ключевые технологии**: Python, `python-telegram-bot`, `OpenAI API`, `Google Sheets API`.
> 📄 **Полная презентация проекта** (PDF, RU): [Персональный ассистент для помощи в достижении поставленных целей](Персональный%20ассистент%20для%20помощи%20в%20достижении%20поставленных%20целей.pdf)

---

## 💡 Примеры использования

Чтобы лучше понять, как бот помогает в достижении целей, рассмотрим несколько сценариев:

### 🌟 Сценарий 1: Установка первой цели

Предположим, ваша цель – "Написать книгу за 3 месяца, уделяя этому по 2 часа в день".

1.  **Вы**: `/start`
    **Бот**: 🤖 Привет! Я — твой персональный ассистент... Жми `/setgoal`!
2.  **Вы**: `/setgoal`
    **Бот**: Какую цель вы хотите достичь? Опишите её как можно подробнее.
3.  **Вы**: Написать книгу "Мои приключения в мире кода"
    **Бот**: За какой срок вы планируете достичь цели (например, 'за 2 месяца', 'за 6 недель', 'за 50 дней')? Укажите срок до 3 месяцев.
4.  **Вы**: за 3 месяца
    **Бот**: Сколько примерно времени вы готовы уделять достижению цели ежедневно (например, '30 минут', '1-2 часа')?
5.  **Вы**: 2 часа в день
    **Бот**: Генерирую для вас персональный план... Это может занять некоторое время.
    *(Через некоторое время)*
    **Бот**: ✅ Ваша цель *Написать книгу "Мои приключения в мире кода"* установлена! План сохранён.
    📄 [Открыть таблицу](https://docs.google.com/spreadsheets/d/ВАША_ССЫЛКА_НА_ТАБЛИЦУ)

    Используйте `/today`, чтобы увидеть задачу на сегодня, и `/check` для отметки выполнения.
6.  **Вы**: `/today`
    **Бот**: 📅 Задача на сегодня (ДД.ММ.ГГГГ, День недели):
    📝 Составить детальный план первой главы книги.
    Статус: Не выполнено
7.  **You**: `/check` -> (выбираете "✅ Выполнено" через кнопки)
    **Бот**: Статус обновлен! 💪
8.  **You**: `/status`
    **Бот**: (показывает прогресс, например: 🎯 *Цель*: Написать книгу... 📊 *Прогресс*: 1% (✅ 1/90 дней)...)

### ☀️ Сценарий 2: Ежедневное взаимодействие

1.  *(Утром)* **Бот** (автоматическое напоминание, если настроено):
    ☀️ Доброе утро! Время взяться за сегодняшнюю задачу для вашей цели!
    📝 Ваша задача: Написать 5 страниц текста для второй главы.
2.  **Вы**: (в течение дня работаете над задачей)
3.  **Вы**: `/check` -> (выбираете "✅ Выполнено")
    **Бот**: Статус обновлен! 💪
4.  **Вы**: `/motivation`
    **Бот**: Отличная работа! Каждый шаг приближает тебя к мечте. Не сбавляй темп! ✨

---

## 🛠️ Возможности

| Команда | Описание |
|---------|----------|
| `/start` | 🚀 Начать работу с ботом |
| `/help`  | ℹ️ Справка по доступным командам |
| `/setgoal` | 🎯 Установить новую цель |
| `/today` | 📅 Задача на сегодня |
| `/check` | ✍️ Отметить выполнение задачи |
| `/status` | 📊 Посмотреть прогресс в достижении цели |
| `/motivation` | 💡 Мотивирующее сообщение |
| `/cancel` | ⛔ Отменить текущую операцию |
| `/reset` | 🗑️ Сбросить все цели (удалить данные полностью) |

Бот хранит всю информацию в индивидуальной Google-таблице:
* лист «Информация о цели» — параметры цели;
* лист «План» — ежедневные задачи с автообновлением статуса.


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
* [Установка на Ubuntu 24.04 LTS](docs/install_ubuntu.md)
* [Архитектура проекта](docs/architecture.md)
* [Список изменений](CHANGELOG.md)

Для разработчиков:
* [Руководство по участию (CONTRIBUTING.md)](CONTRIBUTING.md)
* [Чек-лист разработки (актуальные задачи)](Чек-лист%20разработки%20(отмечать%20выполненное).md)

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

Проект распространяется по лицензии MIT. 
