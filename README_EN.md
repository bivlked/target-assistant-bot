# Target Assistant Bot

[![CI/CD Pipeline](https://github.com/bivlked/target-assistant-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/bivlked/target-assistant-bot/actions/workflows/ci.yml)
[![Tests & Coverage](https://github.com/bivlked/target-assistant-bot/actions/workflows/tests.yml/badge.svg)](https://github.com/bivlked/target-assistant-bot/actions/workflows/tests.yml)
[![Coverage Status](https://codecov.io/gh/bivlked/target-assistant-bot/branch/main/graph/badge.svg)](https://codecov.io/gh/bivlked/target-assistant-bot)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

Personal Telegram assistant that helps you set goals, break them down into daily tasks and track progress. All data is stored in **Google Sheets**; planning and motivational messages are powered by **OpenAI**.

> 🚀 **Project Goal**: To create a smart and responsive assistant for effective progress towards long-term goals.
> 🎯 **Key Technologies**: Python, `python-telegram-bot`, `OpenAI API`, `Google Sheets API`.
> 📄 **Full Project Pitch** (PDF, Russian): [Personal assistant for helping to achieve goals](Персональный%20ассистент%20для%20помощи%20в%20достижении%20поставленных%20целей.pdf)

---

## 💡 Usage Scenarios

To better understand how the bot helps in achieving goals, let's consider a few scenarios:

### 🌟 Scenario 1: Setting Your First Goal

Let's say your goal is "Write a book in 3 months, dedicating 2 hours цьому daily."

1.  **You**: `/start`
    **Bot**: 🤖 Hello! I'm your personal goal assistant... Press `/setgoal` to begin!
2.  **You**: `/setgoal`
    **Bot**: What goal do you want to achieve? Describe it in as much detail as possible.
3.  **You**: Write a book "My Adventures in the World of Code"
    **Bot**: What is the deadline for achieving your goal (e.g., 'in 2 months', 'in 6 weeks', 'in 50 days')? Please specify a period up to 3 months.
4.  **You**: in 3 months
    **Bot**: How much time are you approximately willing to dedicate to achieving your goal daily (e.g., '30 minutes', '1-2 hours')?
5.  **You**: 2 hours a day
    **Bot**: Generating your personal plan... This might take a moment.
    *(After a short while)*
    **Bot**: ✅ Your goal *Write a book "My Adventures in the World of Code"* is set! The plan has been saved.
    📄 [Open Spreadsheet](https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_LINK)

    Use `/today` to see today's task, and `/check` to mark it as complete.
6.  **You**: `/today`
    **Bot**: 📅 Task for today (15.05.2025, Wednesday):
    📝 Outline the first chapter of the book.
    Status: Not completed
7.  **You**: `/check` -> (select "✅ Done" via buttons)
    **Bot**: Status updated! 💪
8.  **You**: `/status`
    **Bot**: (shows progress, e.g., 🎯 *Goal*: Write a book... 📊 *Progress*: 1% (✅ 1/90 days)...)

### ☀️ Scenario 2: Daily Interaction

1.  *(Morning)* **Bot** (automatic reminder, if configured):
    ☀️ Good morning! Time to tackle today's task for your goal!
    📝 Your task: Write 5 pages of text for the second chapter.
2.  **You**: (work on the task during the day)
3.  **You**: `/check` -> (select "✅ Done")
    **Bot**: Status updated! 💪
4.  **You**: `/motivation`
    **Bot**: Great job! Every step brings you closer to your dream. Keep up the pace! ✨

---

## 🛠️ Features

| Command | Description |
|---------|-------------|
| `/start` | 🚀 Start using the bot |
| `/help`  | ℹ️ Show available commands |
| `/setgoal` | 🎯 Set a new goal |
| `/today` | 📅 Task for today |
| `/check` | ✍️ Mark task as completed |
| `/status` | 📊 Show progress towards goal |
| `/motivation` | 💡 Get a motivational message |
| `/cancel` | ⛔ Cancel current operation |
| `/reset` | 🗑️ Remove all goals (delete data completely) |

For every Telegram user the bot creates a personal Google Spreadsheet:
* sheet **Goal Info** — goal parameters;
* sheet **Plan** — a list of daily tasks with auto-updated status.

## 🚀 Quick start (local `venv`)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# environment variables
cp .env.example .env
$EDITOR .env  # set TELEGRAM_BOT_TOKEN and GOOGLE_CREDENTIALS_PATH

python main.py
```

## 🐳 Quick start (Docker Compose)

```bash
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
cp .env.example .env
# edit .env, then run:
docker compose up -d --build
```

## ☁️ Deploy on a server (systemd)

1. Clone the repository and set up the environment:

```bash
sudo apt update && sudo apt install -y python3 python3-venv git
sudo useradd -m targetbot
sudo -iu targetbot

# clone
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy your `google_credentials.json` and fill in `.env` (use `env.example` as a template).

3. Copy the systemd unit file and start the service:

```bash
sudo cp deploy/targetbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now targetbot.service
```

4. (Optional) Enable auto-update:

```bash
sudo cp deploy/update-bot.sh /usr/local/bin/update-bot.sh
# check for updates every 15 minutes
echo "*/15 * * * * root /usr/local/bin/update-bot.sh >> /var/log/targetbot_update.log 2>&1" | sudo tee /etc/cron.d/targetbot-update
```

## 📚 Documentation & Resources

* [User guide](docs/user_guide.md) *(Russian)*
* [Install on Ubuntu 24.04 LTS](docs/install_ubuntu.md) *(Russian)*
* [Project architecture](docs/architecture.md) *(Russian)*
* [Changelog](CHANGELOG.md)

For Developers:
* [Contribution Guidelines (CONTRIBUTING.md)](CONTRIBUTING.md)
* [Development Checklist (current tasks - RU)](Чек-лист%20разработки%20(отмечать%20выполненное).md)

---

## 📜 License

Distributed under the MIT License. 