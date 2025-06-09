<div align="center">
  <img src="https://raw.githubusercontent.com/bivlked/target-assistant-bot/main/.github/assets/logo.svg" alt="Target Assistant Bot Logo" width="250" height="250">
  
  <h1>🎯 Target Assistant Bot</h1>
  
  <p>
    <strong>Ваш персональный AI-ассистент для достижения любых целей</strong><br>
    <sub>Умный помощник, который разбивает большие цели на ежедневные задачи и следит за прогрессом</sub>
  </p>

  <p>
    <a href="README_EN.md">🌐 English Version</a> •
    <a href="#-ключевые-возможности">✨ Возможности</a> •
    <a href="#-быстрый-старт">🚀 Быстрый старт</a> •
    <a href="#-документация">📖 Документация</a>
  </p>

  <!-- Основные бейджи -->
  <p>
    <a href="https://github.com/bivlked/target-assistant-bot/releases/latest">
      <img src="https://img.shields.io/github/v/release/bivlked/target-assistant-bot?style=flat-square&logo=github&label=Version&color=blue" alt="Latest Release">
    </a>
    <a href="https://github.com/bivlked/target-assistant-bot/actions/workflows/tests.yml">
      <img src="https://img.shields.io/github/actions/workflow/status/bivlked/target-assistant-bot/tests.yml?branch=main&style=flat-square&logo=github-actions&label=Tests" alt="Tests Status">
    </a>
    <a href="https://codecov.io/gh/bivlked/target-assistant-bot">
      <img src="https://img.shields.io/codecov/c/github/bivlked/target-assistant-bot?style=flat-square&logo=codecov&label=Coverage" alt="Code Coverage">
    </a>
    <a href="https://github.com/bivlked/target-assistant-bot/blob/main/LICENSE">
      <img src="https://img.shields.io/github/license/bivlked/target-assistant-bot?style=flat-square&label=License" alt="License">
    </a>
  </p>
  <!-- Технологии -->
  <p>
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Telegram-Bot%20API-2CA5E0?style=flat-square&logo=telegram&logoColor=white" alt="Telegram Bot API">
    <img src="https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=flat-square&logo=openai&logoColor=white" alt="OpenAI">
    <img src="https://img.shields.io/badge/Google%20Sheets-API-34A853?style=flat-square&logo=google-sheets&logoColor=white" alt="Google Sheets">
    <img src="https://img.shields.io/badge/Docker-Container-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
  </p>
  <!-- Дополнительные бейджи -->
  <p>
    <a href="https://github.com/psf/black">
      <img src="https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square" alt="Code style: black">
    </a>
    <a href="https://github.com/charliermarsh/ruff">
      <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json&style=flat-square" alt="Ruff">
    </a>
    <a href="https://mypy-lang.org/">
      <img src="https://img.shields.io/badge/type_checker-mypy-blue.svg?style=flat-square" alt="Checked with mypy">
    </a>
    <a href="https://github.com/bivlked/target-assistant-bot/commits/main">
      <img src="https://img.shields.io/github/last-commit/bivlked/target-assistant-bot?style=flat-square&logo=github" alt="Last Commit">
    </a>
    <a href="https://github.com/bivlked/target-assistant-bot/issues">
      <img src="https://img.shields.io/github/issues/bivlked/target-assistant-bot?style=flat-square&logo=github" alt="Issues">
    </a>
  </p>
</div>

---

<div align="center">
  <table>
    <tr>
      <td align="center" width="33%">
        🚀
        <br>
        <strong>Мгновенный старт</strong>
        <br>
        <sub>Начните достигать целей через 5 минут</sub>
      </td>
      <td align="center" width="33%">
        🧠
        <br>
        <strong>Умный AI-планировщик</strong>
        <br>
        <sub>GPT-4o-mini создает оптимальные планы</sub>
      </td>
      <td align="center" width="33%">
        📈
        <br>
        <strong>Отслеживание прогресса</strong>
        <br>
        <sub>Визуализация в Google Sheets</sub>
      </td>
    </tr>
  </table>
</div>

## 🌟 Ключевые возможности

### 🎯 Управление множественными целями
- **До 10 активных целей** одновременно
- **Приоритеты**: 🔴 Высокий • 🟡 Средний • 🟢 Низкий
- **Теги** для группировки: #работа #здоровье #саморазвитие
- **Статусы**: ✅ Активная • 🏆 Завершенная • 📦 В архиве

### 🤖 AI-планирование с GPT-4o-mini
- Автоматическое создание **SMART-планов**
- Разбивка на **ежедневные задачи**
- Учет вашего **расписания и возможностей**
- **Умная генерация** планов с учетом целей

### 📊 Аналитика и отчеты
- **Реальный прогресс** по каждой цели
- **Статистика выполнения** задач
- **Детальная аналитика** в Google Sheets
- **Экспорт в Google Sheets**

### 💬 Удобный интерфейс
- **Inline-кнопки** для быстрых действий
- **Пошаговый wizard** создания целей
- **Настраиваемые напоминания** (через переменные окружения)
- **Мотивационные сообщения** от AI

## 📊 Архитектура системы

```mermaid
graph TB
    subgraph "👤 Пользователь"
        A[Telegram App]
    end
    
    subgraph "🤖 Target Assistant Bot"
        B[Bot Interface]
        C[Goal Manager]
        D[Task Scheduler]
        E[Analytics Engine]
    end
    
    subgraph "🧠 AI Services"
        F[OpenAI GPT-4o-mini]
        G[Plan Generator]
        H[Motivation Engine]
    end
    
    subgraph "💾 Data Storage"
        I[Google Sheets API]
        J[User Goals]
        K[Daily Tasks]
        L[Progress Tracking]
    end
    
    A <--> B
    B --> C
    C --> D
    C --> E
    C <--> G
    G <--> F
    H <--> F
    D --> H
    C <--> I
    I --> J
    I --> K
    I --> L
    
    style A fill:#2CA5E0,stroke:#fff,color:#fff
    style F fill:#412991,stroke:#fff,color:#fff
    style I fill:#34A853,stroke:#fff,color:#fff
```

## 🚀 Быстрый старт

### 🐳 Запуск через Docker (рекомендуется)

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot

# 2. Создайте файл с настройками
cp .env.example .env

# 3. Заполните обязательные параметры в .env:
# - TELEGRAM_BOT_TOKEN (получите у @BotFather)
# - OPENAI_API_KEY (получите на platform.openai.com)
# - Добавьте google_credentials.json

# 4. Запустите бота
docker compose up -d
```

### 🐍 Локальная установка

<details>
<summary>Развернуть инструкцию</summary>

```bash
# 1. Создайте виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows

# 2. Установите зависимости
pip install -r requirements.txt

# 3. Настройте переменные окружения
cp .env.example .env
# Отредактируйте .env файл

# 4. Запустите бота
python main.py
```

</details>

### ☁️ Деплой на сервер

<details>
<summary>Развернуть инструкцию для Ubuntu/Debian</summary>

```bash
# 1. Установите зависимости
sudo apt update && sudo apt install -y python3.11 python3.11-venv git

# 2. Создайте пользователя для бота
sudo useradd -m -s /bin/bash targetbot
sudo -u targetbot -i

# 3. Клонируйте и настройте
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Настройте systemd сервис
sudo cp deploy/targetbot.service /etc/systemd/system/
sudo systemctl enable --now targetbot
```

Подробная инструкция: [📖 Установка на Ubuntu](docs/install_ubuntu_detailed.md)

</details>

## 📖 Примеры использования

### 🎯 Создание первой цели

```
👤: /start
🤖: Добро пожаловать в Target Assistant Bot! 🎯
    
    Я помогу вам достигать любых целей, разбивая их на 
    конкретные ежедневные задачи.
    
    [🎯 Мои цели] [➕ Создать цель] [📊 Открыть таблицу]

👤: [Нажимает ➕ Создать цель]
🤖: Шаг 1/6: Введите название цели
    Например: "Изучить Python", "Похудеть на 10 кг"

👤: Выучить английский до уровня B2
🤖: Шаг 2/6: Опишите подробнее, чего хотите достичь?

... [пошаговый процесс создания] ...

🤖: ✅ Цель создана! Я составил план на 90 дней.
    Первая задача на завтра:
    📝 Пройти тест на определение текущего уровня
```

### 📅 Ежедневная работа

```
🤖: ☀️ Доброе утро! Ваши задачи на сегодня:

📚 Английский язык (🔴 высокий приоритет)
└─ Выучить 20 новых слов по теме "Бизнес"

🏃 Здоровье (🟡 средний приоритет)  
└─ Пробежка 3 км в парке

💻 Программирование (🟢 низкий приоритет)
└─ Прочитать главу про ООП в Python

[✅ Отметить выполнение] [📊 Статистика]
```

## 📋 Полный список команд

| Команда | Описание | Пример |
|---------|----------|--------|
| `/start` | 🚀 Начало работы с ботом | `/start` |
| `/my_goals` | 🎯 Управление всеми целями | `/my_goals` |
| `/add_goal` | ➕ Создать новую цель | `/add_goal` |
| `/today` | 📅 Задачи на сегодня | `/today` |
| `/check` | ✅ Отметить выполнение | `/check` |
| `/status` | 📊 Общая статистика | `/status` |
| `/motivation` | 💪 Получить мотивацию | `/motivation` |
| `/help` | ❓ Справка по командам | `/help` |
| `/reset` | 🗑️ Удалить все данные | `/reset` |

## 🛠️ Технологический стек

<div align="center">
  <table>
    <tr>
      <th>Категория</th>
      <th>Технологии</th>
    </tr>
    <tr>
      <td><strong>🐍 Язык</strong></td>
      <td>Python 3.12+ с полной типизацией</td>
    </tr>
    <tr>
      <td><strong>🤖 Telegram</strong></td>
      <td>python-telegram-bot 22.0 (async)</td>
    </tr>
    <tr>
      <td><strong>🧠 AI</strong></td>
      <td>OpenAI GPT-4o-mini API</td>
    </tr>
    <tr>
      <td><strong>💾 Хранение</strong></td>
      <td>Google Sheets API v4</td>
    </tr>
    <tr>
      <td><strong>🔄 Асинхронность</strong></td>
      <td>asyncio</td>
    </tr>
    <tr>
      <td><strong>⏰ Планировщик</strong></td>
      <td>APScheduler</td>
    </tr>
    <tr>
      <td><strong>🧪 Тестирование</strong></td>
      <td>pytest, pytest-asyncio, coverage</td>
    </tr>
    <tr>
      <td><strong>📊 Мониторинг</strong></td>
      <td>Prometheus, Sentry</td>
    </tr>
    <tr>
      <td><strong>🐳 Контейнеризация</strong></td>
      <td>Docker, Docker Compose</td>
    </tr>
    <tr>
      <td><strong>🔧 CI/CD</strong></td>
      <td>GitHub Actions</td>
    </tr>
  </table>
</div>

## 📚 Документация

### 📖 Для пользователей
- [**Руководство пользователя**](docs/user_guide.md) - подробная инструкция по использованию
- [**FAQ**](docs/faq.md) - ответы на частые вопросы
- [**Примеры целей**](docs/examples.md) - идеи и шаблоны целей

### 🛠️ Для разработчиков
- [**Архитектура проекта**](docs/architecture.md) - техническое описание
- [**API документация**](https://bivlked.github.io/target-assistant-bot/) - автогенерируемая документация
- [**Руководство контрибьютора**](CONTRIBUTING.md) - как внести свой вклад
- [**Чек-лист разработки**](DEVELOPMENT_CHECKLIST.md) - roadmap и задачи

### 🚀 Установка и настройка
- [**Быстрая установка**](docs/install_ubuntu.md) - краткая инструкция
- [**Подробная установка**](docs/install_ubuntu_detailed.md) - пошаговое руководство
- [**Настройка Google Sheets**](docs/google_sheets_setup.md) - создание service account
- [**Переменные окружения**](.env.example) - описание всех параметров

## 🤝 Как внести свой вклад

Мы рады любому вкладу в развитие проекта! 

```mermaid
graph LR
    A[🐛 Нашли баг?] --> B[Создайте Issue]
    C[💡 Есть идея?] --> D[Обсудите в Discussions]
    E[💻 Хотите помочь?] --> F[Сделайте Pull Request]
    
    B --> G[Мы исправим!]
    D --> H[Обсудим вместе!]
    F --> I[Review и merge!]
    
    style A fill:#ff6b6b,stroke:#fff,color:#fff
    style C fill:#4ecdc4,stroke:#fff,color:#fff
    style E fill:#45b7d1,stroke:#fff,color:#fff
```

Прочитайте [CONTRIBUTING.md](CONTRIBUTING.md) для подробной информации.

## 📈 Статистика проекта

<div align="center">
  <img src="https://repobeats.axiom.co/api/embed/9df92afe031ab7ae4a8df6f266e0c923f6561425.svg" alt="Repobeats analytics" />
</div>

## 🏆 Контрибьюторы

<a href="https://github.com/bivlked/target-assistant-bot/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=bivlked/target-assistant-bot" />
</a>

## 📜 Лицензия

Этот проект распространяется под лицензией MIT. Подробности в файле [LICENSE](LICENSE).

---

<div align="center">
  
### ⭐ Поддержите проект

Если Target Assistant Bot помог вам в достижении целей, поставьте звезду!

[![Star History Chart](https://api.star-history.com/svg?repos=bivlked/target-assistant-bot&type=Date)](https://star-history.com/#bivlked/target-assistant-bot&Date)

<br>

**Сделано с ❤️ by [bivlked](https://github.com/bivlked)**

<sub>
  Есть вопросы? Создайте <a href="https://github.com/bivlked/target-assistant-bot/issues/new">Issue</a> • 
  Хотите обсудить? Заходите в <a href="https://github.com/bivlked/target-assistant-bot/discussions">Discussions</a> •
  Нужна помощь? Пишите в <a href="https://t.me/targetassistant_support">Telegram</a>
</sub>

</div> 
