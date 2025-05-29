# Target Assistant Bot

[![CI/CD Pipeline](https://github.com/bivlked/target-assistant-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/bivlked/target-assistant-bot/actions/workflows/ci.yml)
[![Tests & Coverage](https://github.com/bivlked/target-assistant-bot/actions/workflows/tests.yml/badge.svg)](https://github.com/bivlked/target-assistant-bot/actions/workflows/tests.yml)
[![Coverage Status](https://codecov.io/gh/bivlked/target-assistant-bot/branch/main/graph/badge.svg)](https://codecov.io/gh/bivlked/target-assistant-bot)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![GitHub Release](https://img.shields.io/github/v/release/bivlked/target-assistant-bot.svg)](https://github.com/bivlked/target-assistant-bot/releases/latest)

Personal Telegram assistant that helps you set goals, break them down into daily tasks and track progress. All data is stored in **Google Sheets**; planning and motivational messages are powered by **OpenAI**. **Now supports up to 10 simultaneous goals!**

> 🚀 **Project Goal**: To create a smart and responsive assistant for effective progress towards long-term goals.
> 🎯 **Key Technologies**: Python, `python-telegram-bot`, `OpenAI API`, `Google Sheets API`.
> 📊 **Status**: v0.2.0 - Production Ready with Multi-Goals Support
> 📄 **Full Project Pitch** (PDF, Russian): [Personal assistant for helping to achieve goals](Персональный%20ассистент%20для%20помощи%20в%20достижении%20поставленных%20целей.pdf)

---

## ✨ What's New in v0.2.0

### 🎯 Multiple Goals Support
- **Up to 10 active goals simultaneously** - no more single goal limitations
- **Priorities** - high 🔴, medium 🟡, low 🟢 for better organization
- **Tags** - organize goals by categories (work, health, self-development)
- **Statuses** - active, completed, archived goals

### 📊 Enhanced Analytics
- **Overall statistics** across all goals with progress tracking
- **Detailed analytics** for each individual goal
- **Progress monitoring** with days remaining and completion pace

### 🎮 Interactive Interface
- **Inline buttons** for quick actions
- **Goal creation wizard** with step-by-step guidance
- **Goal management** through convenient menus

## 💡 Usage Scenarios

### 🌟 New Scenario: Managing Multiple Goals

Imagine you have several goals:
1. "Learn Python in 3 months" (🔴 high priority)
2. "Run a half marathon" (🟡 medium priority)
3. "Read 20 books in a year" (🟢 low priority)

**Creating your first goal:**
1. **You**: `/start`
   **Bot**: 🎯 Welcome to Target Assistant Bot! I'll help you manage up to 10 goals simultaneously...
2. **You**: `/my_goals`
   **Bot**: 📝 You don't have any goals yet. Use /add_goal to create a new goal.
3. **You**: Click "➕ Add Goal" button
   **Bot**: 🎯 Creating new goal. Step 1/6: Enter a short goal name...

**Managing multiple goals:**
4. **You**: `/today`
   **Bot**: 📅 Tasks for today:
   🔴 **Learn Python**: Master OOP basics in Python
   🟡 **Half Marathon**: Run 5km at slow pace
   🟢 **Reading Books**: Read 30 pages of "Clean Code"

5. **You**: `/status`
   **Bot**: 📊 Overall goal status:
   • Total goals: 3
   • Active: 3
   • Overall progress: 35%
   
   🎯 Active goals:
   🔴 **Learn Python** - 45% • 📅 15.04.2025
   🟡 **Half Marathon** - 30% • 📅 01.05.2025
   🟢 **Reading Books** - 25% • 📅 31.12.2025

### ☀️ New Daily Interaction

**Morning reminder (automatic):**
**Bot**: ☀️ Good morning! Your tasks for today:
• **Learn Python**: Create your first Python class
• **Half Marathon**: Light 3km jog

[📝 Mark completion] [📊 Overall status]

**Quick completion marking:**
**You**: Click "📝 Mark completion"
**Bot**: 📝 Choose task to update status:
- Learn Python: Create your first class...
- Half Marathon: Light 3km jog

---

## 🛠️ Features

### Core Commands

| Command | Description |
|---------|-------------|
| `/start` | 🚀 Start using the bot |
| `/help`  | ℹ️ Show available commands |
| `/my_goals` | 🎯 **[NEW]** Manage all goals - main command |
| `/add_goal` | ➕ **[NEW]** Create new goal through interactive interface |
| `/setgoal` | 🎯 Create goal through text dialog (legacy) |
| `/today` | 📅 **[UPDATED]** All tasks for today from all active goals |
| `/check` | ✍️ **[UPDATED]** Mark completion with specific goal selection |
| `/status` | 📊 **[UPDATED]** Overall progress across all goals |
| `/motivation` | 💡 **[UPDATED]** Motivation based on all your goals |
| `/cancel` | ⛔ Cancel current operation |
| `/reset` | 🗑️ Remove all goals (delete data completely) |

### New Capabilities

- **🎯 Up to 10 simultaneous goals** - work on multiple directions
- **📊 Priorities** - high (🔴), medium (🟡), low (🟢)
- **🏷️ Tags** - organize goals by categories
- **📋 Interactive management** - buttons for all actions
- **📈 Extended statistics** - detailed analytics for each goal
- **🔄 Auto-migration** - existing goals automatically transferred to new format

### Data Storage Structure

The bot creates an individual Google Spreadsheet with improved structure:
* **"Goals List"** — main sheet with all your goals, their statuses and progress
* **"Goal 1", "Goal 2", ..., "Goal 10"** — separate sheets with plans for each goal
* **Automatic migration** — existing data is transferred to new format

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
# This script will now pull the latest release tag by default.
# Check for updates e.g., every 15 minutes
echo "*/15 * * * * root /usr/local/bin/update-bot.sh >> /var/log/targetbot_update.log 2>&1" | sudo tee /etc/cron.d/targetbot-update
```

## 📚 Documentation & Resources

* [User guide](docs/user_guide.md) *(Russian)*
* [Install on Ubuntu (brief)](docs/install_ubuntu.md) *(Russian)*
* [Install on Ubuntu (detailed)](docs/install_ubuntu_detailed.md) *(Russian)*
* [Project architecture](docs/architecture.md) *(Russian)*
* [Changelog](CHANGELOG.md)

For Developers:
* [Contribution Guidelines (CONTRIBUTING.md)](CONTRIBUTING.md)
* [Development Checklist (current tasks - RU)](DEVELOPMENT_CHECKLIST.md)

---

## 📖 Building API Documentation (Sphinx)

The project's API documentation is generated from docstrings using [Sphinx](https://www.sphinx-doc.org/).

**To build the documentation locally:**

1.  Ensure you are in an activated virtual environment with all dependencies installed (including those in the `# --- Documentation ---` section of `requirements.txt`).
2.  Navigate to the `docs/` directory:
    ```bash
    cd docs
    ```
3.  Run the build command:
    *   For Linux/macOS/Git Bash:
        ```bash
        make html
        ```
    *   For Windows (CMD/PowerShell):
        ```bash
        .\make.bat html
        ```
4.  The generated documentation will be available in the `docs/build/html/` directory. Open `index.html` in your browser.

---

## 📜 License

Distributed under the MIT License. 