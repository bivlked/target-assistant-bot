# 🚀 Быстрая установка на Ubuntu/Debian

<div align="center">
  <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Rocket.png" width="100">
  
  <p>
    <strong>Установка Target Assistant Bot за 5 минут</strong><br>
    <sub>Краткая инструкция для опытных пользователей</sub>
  </p>
</div>

## 📋 Требования

- Ubuntu 20.04+ или Debian 11+
- Python 3.11+
- Git
- Доступ к серверу по SSH

## ⚡ Быстрая установка

```bash
# 1. Обновление системы
sudo apt update && sudo apt upgrade -y

# 2. Установка зависимостей
sudo apt install -y python3.11 python3.11-venv python3-pip git

# 3. Создание пользователя для бота
sudo useradd -m -s /bin/bash targetbot
sudo -u targetbot -i

# 4. Клонирование репозитория
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot

# 5. Создание виртуального окружения
python3.11 -m venv .venv
source .venv/bin/activate

# 6. Установка зависимостей
pip install -r requirements.txt

# 7. Настройка конфигурации
cp .env.example .env
nano .env  # Заполните необходимые параметры

# 8. Добавление Google credentials
# Скопируйте ваш google_credentials.json в папку проекта

# 9. Настройка команд бота
python setup_commands.py

# 10. Запуск бота
python main.py
```

## 🐳 Установка через Docker

```bash
# 1. Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 2. Клонирование и настройка
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
cp .env.example .env
nano .env

# 3. Запуск
docker compose up -d
```

## 🔧 Systemd сервис

```bash
# 1. Копирование файла сервиса
sudo cp deploy/targetbot.service /etc/systemd/system/

# 2. Редактирование пути в сервисе
sudo nano /etc/systemd/system/targetbot.service

# 3. Запуск и включение автозапуска
sudo systemctl daemon-reload
sudo systemctl enable targetbot
sudo systemctl start targetbot

# 4. Проверка статуса
sudo systemctl status targetbot
```

## ❓ Проблемы?

- 📖 [Подробная инструкция](install_ubuntu_detailed.md)
- 💬 [FAQ](faq.md)
- 🐛 [Создать Issue](https://github.com/bivlked/target-assistant-bot/issues/new)

---

<div align="center">
  <a href="../README.md">← Вернуться к README</a> • 
  <a href="install_ubuntu_detailed.md">Подробная инструкция →</a>
</div>

# Установка на Ubuntu 24.04 LTS (Minimal)

Ниже приведены *два* рекомендованных способа развернуть **Target-Assistant-Bot** на чистой Ubuntu 24.04 LTS Minimal.

> Все команды выполнять от имени пользователя с правами sudo.

---

## Способ 1 — virtualenv (systemd-служба)

### 1️⃣ Подготовка системы
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv git build-essential
```

### 2️⃣ Клонирование репозитория
```bash
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
```

### 3️⃣ Создание виртуального окружения
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

### 4️⃣ Настройка переменных окружения
```bash
cp .env.example .env
nano .env           # заполните TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, GOOGLE_CREDENTIALS_PATH и др.
```

### 5️⃣ Проверка запуска
```bash
source .venv/bin/activate
python main.py
```

### 6️⃣ Создание systemd-службы
```bash
sudo tee /etc/systemd/system/target-assistant-bot.service > /dev/null <<'EOF'
[Unit]
Description=Target Assistant Telegram Bot
After=network-online.target

[Service]
Type=simple
User=%i            # замените на имя пользователя, где расположен бот
WorkingDirectory=/home/%i/target-assistant-bot
EnvironmentFile=/home/%i/target-assistant-bot/.env
ExecStart=/home/%i/target-assistant-bot/.venv/bin/python main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now target-assistant-bot.service
```

Бот теперь стартует автоматически после перезагрузки.

---

## Способ 2 — Docker Compose

### 1️⃣ Установка Docker
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker  # применяем изменения группы без выхода
```

### 2️⃣ Клонирование репозитория и подготовка
```bash
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
cp .env.example .env
nano .env  # заполните переменные
```

### 3️⃣ Запуск контейнера
```bash
docker compose up -d --build
```

### 4️⃣ Логи
```bash
docker compose logs -f
```

### Обновление
```bash
git pull
# при необходимости
docker compose build
docker compose up -d
```

---

## Обновление команд BotFather
Однократно выполните:
```bash
source .venv/bin/activate  # или docker exec -it <container> bash
python setup_commands.py --force
```

---

### Возможные проблемы
| Симптом | Решение |
|----------|---------|
| `google.auth.exceptions.DefaultCredentialsError` | Проверьте путь к service-account JSON в переменной `GOOGLE_CREDENTIALS_PATH`. |
| `Timed out` при старте | Разрешите выход в интернет/прокси для доступа к Telegram и Google API. | 