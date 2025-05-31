# 📖 Подробная инструкция установки на Ubuntu/Debian

<div align="center">
  <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Books.png" width="100">
  
  <p>
    <strong>Пошаговая установка Target Assistant Bot</strong><br>
    <sub>Детальное руководство с объяснениями каждого шага</sub>
  </p>
</div>

## 📋 Содержание

- [🔍 Проверка требований](#-проверка-требований)
- [🛠️ Подготовка системы](#️-подготовка-системы)
- [🐍 Установка Python 3.11](#-установка-python-311)
- [👤 Создание пользователя](#-создание-пользователя)
- [📦 Установка бота](#-установка-бота)
- [⚙️ Настройка конфигурации](#️-настройка-конфигурации)
- [🚀 Первый запуск](#-первый-запуск)
- [🔧 Настройка автозапуска](#-настройка-автозапуска)
- [🐳 Docker альтернатива](#-docker-альтернатива)
- [❓ Решение проблем](#-решение-проблем)

---

## 🔍 Проверка требований

### Минимальные требования
- **ОС**: Ubuntu 20.04+ или Debian 11+
- **RAM**: 512 MB минимум (рекомендуется 1 GB)
- **Диск**: 1 GB свободного места
- **CPU**: 1 ядро (рекомендуется 2)
- **Сеть**: Стабильное интернет-соединение

### Проверка версии системы
```bash
# Проверка версии Ubuntu
lsb_release -a

# Проверка свободного места
df -h

# Проверка оперативной памяти
free -h

# Проверка процессора
lscpu
```

---

## 🛠️ Подготовка системы

### 1. Обновление пакетов

```bash
# Обновление списка пакетов
sudo apt update

# Обновление установленных пакетов
sudo apt upgrade -y

# Установка базовых утилит
sudo apt install -y curl wget git nano htop
```

### 2. Настройка файрвола (опционально)

```bash
# Установка ufw если не установлен
sudo apt install -y ufw

# Разрешение SSH (если используете)
sudo ufw allow ssh

# Включение файрвола
sudo ufw enable
```

---

## 🐍 Установка Python 3.11

### Вариант 1: Из официальных репозиториев (Ubuntu 22.04+)

```bash
# Установка Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Проверка версии
python3.11 --version
```

### Вариант 2: Через deadsnakes PPA (Ubuntu 20.04)

```bash
# Добавление репозитория
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# Установка Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Установка pip для Python 3.11
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
```

### Проверка установки

```bash
# Должно вывести: Python 3.11.x
python3.11 --version

# Проверка pip
python3.11 -m pip --version
```

---

## 👤 Создание пользователя

### Зачем отдельный пользователь?
- 🔒 Безопасность: изоляция процесса бота
- 📁 Организация: все файлы в одном месте
- 🔧 Управление: легко управлять правами

### Создание пользователя

```bash
# Создание пользователя targetbot
sudo useradd -m -s /bin/bash targetbot

# Установка пароля (опционально)
sudo passwd targetbot

# Добавление в группу sudo (если нужно)
sudo usermod -aG sudo targetbot

# Переключение на пользователя
sudo -u targetbot -i
```

---

## 📦 Установка бота

### 1. Клонирование репозитория

```bash
# Переход в домашнюю директорию
cd ~

# Клонирование репозитория
git clone https://github.com/bivlked/target-assistant-bot.git

# Переход в папку проекта
cd target-assistant-bot
```

### 2. Создание виртуального окружения

```bash
# Создание venv
python3.11 -m venv .venv

# Активация venv
source .venv/bin/activate

# Обновление pip
pip install --upgrade pip
```

### 3. Установка зависимостей

```bash
# Установка production зависимостей
pip install -r requirements.txt

# Для разработки (опционально)
pip install -r requirements-dev.txt
```

---

## ⚙️ Настройка конфигурации

### 1. Создание файла .env

```bash
# Копирование примера
cp .env.example .env

# Редактирование файла
nano .env
```

### 2. Заполнение параметров

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# OpenAI API
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY_HERE

# Google Sheets
GOOGLE_CREDENTIALS_PATH=google_credentials.json

# Опциональные параметры
SENTRY_DSN=https://YOUR_SENTRY_DSN_HERE
PROMETHEUS_PORT=8000
LOG_LEVEL=INFO
```

### 3. Настройка Google Sheets

#### Получение Service Account:
1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите Google Sheets API
4. Создайте Service Account
5. Скачайте JSON ключ

#### Добавление credentials:
```bash
# Создайте файл google_credentials.json
nano google_credentials.json

# Вставьте содержимое скачанного JSON файла
# Сохраните: Ctrl+X, Y, Enter

# Проверка прав доступа
chmod 600 google_credentials.json
```

### 4. Настройка команд бота

```bash
# Активируйте venv если не активирован
source .venv/bin/activate

# Запустите скрипт настройки
python setup_commands.py
```

---

## 🚀 Первый запуск

### 1. Тестовый запуск

```bash
# Активация venv
source .venv/bin/activate

# Запуск бота
python main.py
```

### 2. Проверка работы

1. Откройте Telegram
2. Найдите вашего бота по username
3. Отправьте команду `/start`
4. Бот должен ответить приветствием

### 3. Просмотр логов

```bash
# Логи выводятся в консоль
# Для выхода: Ctrl+C

# Запуск в фоне с логами
nohup python main.py > bot.log 2>&1 &

# Просмотр логов
tail -f bot.log
```

---

## 🔧 Настройка автозапуска

### Systemd сервис

#### 1. Создание файла сервиса

```bash
# Вернитесь под обычного пользователя
exit

# Создайте файл сервиса
sudo nano /etc/systemd/system/targetbot.service
```

#### 2. Содержимое файла

```ini
[Unit]
Description=Target Assistant Bot
After=network.target

[Service]
Type=simple
User=targetbot
WorkingDirectory=/home/targetbot/target-assistant-bot
Environment="PATH=/home/targetbot/target-assistant-bot/.venv/bin"
ExecStart=/home/targetbot/target-assistant-bot/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 3. Активация сервиса

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable targetbot

# Запуск сервиса
sudo systemctl start targetbot

# Проверка статуса
sudo systemctl status targetbot
```

#### 4. Управление сервисом

```bash
# Остановка
sudo systemctl stop targetbot

# Перезапуск
sudo systemctl restart targetbot

# Просмотр логов
sudo journalctl -u targetbot -f
```

---

## 🐳 Docker альтернатива

### Установка Docker

```bash
# Установка Docker одной командой
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Перелогиньтесь для применения изменений
exit
# Войдите снова
```

### Запуск через Docker Compose

```bash
# Клонирование репозитория
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot

# Настройка конфигурации
cp .env.example .env
nano .env

# Добавление google_credentials.json
nano google_credentials.json

# Запуск
docker compose up -d

# Просмотр логов
docker compose logs -f
```

### Управление Docker контейнером

```bash
# Остановка
docker compose down

# Перезапуск
docker compose restart

# Обновление
docker compose pull
docker compose up -d
```

---

## ❓ Решение проблем

### Проблема: ModuleNotFoundError

```bash
# Убедитесь, что venv активирован
source .venv/bin/activate

# Переустановите зависимости
pip install -r requirements.txt
```

### Проблема: Permission denied

```bash
# Проверьте права на файлы
ls -la

# Исправьте владельца
sudo chown -R targetbot:targetbot /home/targetbot/target-assistant-bot
```

### Проблема: Bot не отвечает

1. Проверьте токен бота в .env
2. Проверьте интернет-соединение
3. Проверьте логи: `sudo journalctl -u targetbot -n 100`

### Проблема: Google Sheets ошибки

1. Проверьте google_credentials.json
2. Убедитесь, что Google Sheets API включен
3. Проверьте права Service Account

---

## 📚 Дополнительные ресурсы

- 📖 [README проекта](../README.md)
- ❓ [FAQ](faq.md)
- 🔧 [Google Sheets настройка](google_sheets_setup.md)
- 💬 [Поддержка](https://t.me/targetassistant_support)

---

<div align="center">
  <p>
    <strong>Нужна помощь?</strong><br>
    Создайте <a href="https://github.com/bivlked/target-assistant-bot/issues/new">Issue</a> с описанием проблемы
  </p>
  
  <br>
  
  <a href="install_ubuntu.md">← Быстрая установка</a> • 
  <a href="../README.md">Главная →</a>
</div> 