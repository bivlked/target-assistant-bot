# Target Assistant Bot

![CI](https://github.com/bivlked/target-assistant-bot/actions/workflows/ci.yml/badge.svg)
![Tests](https://github.com/bivlked/target-assistant-bot/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10-3.12-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Персональный Telegram-бот-ассистент, который помогает формулировать цели, разбивать их на ежедневные задачи и отслеживать прогресс с сохранением в Google Sheets.

> 📄 Полная презентация проекта: [Персональный ассистент для помощи в достижении поставленных целей (PDF)](Персональный%20ассистент%20для%20помощи%20в%20достижении%20поставленных%20целей.pdf)

---

## Возможности

| Команда | Описание |
|---------|----------|
| `/start` | 🚀 Начать работу с ботом |
| `/help`  | ℹ️ Справка по доступным командам |
| `/setgoal` | 🎯 Установить новую цель |
| `/today` | 📅 Задача на сегодня |
| `/today_async` | ⚡ Асинхронная задача на сегодня (тест) |
| `/check` | ✍️ Отметить выполнение задачи |
| `/status` | 📊 Посмотреть прогресс в достижении цели |
| `/motivation` | 💡 Мотивирующее сообщение |
| `/cancel` | ⛔ Отменить текущую операцию |
| `/reset` | 🗑️ Сбросить все цели (удалить данные полностью) |

Бот хранит всю информацию в индивидуальной Google-таблице:
* лист «Информация о цели» — параметры цели;
* лист «План» — ежедневные задачи с автообновлением статуса.


## Быстрый старт (venv)

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

## Быстрый старт (Docker Compose)

```bash
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
cp .env.example .env
# Отредактируйте .env, затем:
docker compose up -d --build
```

## Деплой на сервер (systemd)

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
# каждые 15 минут проверяем обновления
echo "*/15 * * * * root /usr/local/bin/update-bot.sh >> /var/log/targetbot_update.log 2>&1" | sudo tee /etc/cron.d/targetbot-update
```

## Документация

* [Руководство пользователя](docs/user_guide.md)
* [Установка на Ubuntu 24.04 LTS](docs/install_ubuntu.md)
* [Архитектура проекта](docs/architecture.md)
* [Список изменений](CHANGELOG.md)

---

## Лицензия

Проект распространяется по лицензии MIT. 
