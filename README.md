# Target Assistant Bot

![CI](https://github.com/bivlked/target-assistant-bot/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Персональный Telegram-бот-ассистент, который помогает формулировать цели, разбивать их на ежедневные задачи и отслеживать прогресс с сохранением в Google Sheets.

> 📄 Полная презентация проекта: [Персональный ассистент для помощи в достижении поставленных целей (PDF)](Персональный%20ассистент%20для%20помощи%20в%20достижении%20поставленных%20целей.pdf)

---

## Возможности

| Команда | Описание |
|---------|----------|
| `/start` | Запуск бота и подключение планировщика напоминаний |
| `/help`  | Справка по доступным командам |
| `/setgoal` | Пошаговый диалог постановки новой цели |
| `/today` | Получить задачу на сегодняшний день |
| `/check` | Отметить статус выполнения задачи |
| `/status` | Краткая статистика по цели |
| `/motivation` | Получить мотивационное сообщение |
| `/reset` | Полный сброс данных пользователя |

Бот хранит всю информацию в индивидуальной Google-таблице:
* лист «Цель» — параметры цели;
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

## Документация

* [Руководство пользователя](docs/user_guide.md)
* [Установка на Ubuntu 24.04 LTS](docs/install_ubuntu.md)
* [Архитектура проекта](docs/architecture.md)
* [Список изменений](CHANGELOG.md)

---

## Лицензия

Проект распространяется по лицензии MIT. 