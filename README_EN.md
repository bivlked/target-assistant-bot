# Target Assistant Bot

![CI](https://github.com/bivlked/target-assistant-bot/actions/workflows/ci.yml/badge.svg)
![Tests](https://github.com/bivlked/target-assistant-bot/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10--3.12-blue.svg)
![Coverage](https://codecov.io/gh/bivlked/target-assistant-bot/branch/main/graph/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Personal Telegram assistant that helps you set goals, break them down into daily tasks and track progress. All data is stored in **Google Sheets**; planning and motivational messages are powered by **OpenAI**.

> 📄 Full project pitch (PDF, Russian): [Personal assistant for helping to achieve goals](Персональный%20ассистент%20для%20помощи%20в%20достижении%20поставленных%20целей.pdf)

---

## Features

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

## Quick start (venv)

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

## Quick start (Docker Compose)

```bash
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
cp .env.example .env
# edit .env, then run:
docker compose up -d --build
```

## Deploy on a server (systemd)

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

## Documentation

* [User guide](docs/user_guide.md) *(Russian)*
* [Install on Ubuntu 24.04 LTS](docs/install_ubuntu.md) *(Russian)*
* [Project architecture](docs/architecture.md) *(Russian)*
* [Changelog](CHANGELOG.md)

---

## License

Distributed under the MIT License. 