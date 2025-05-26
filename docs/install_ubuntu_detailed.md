# 📖 Подробная инструкция по установке Target Assistant Bot на Ubuntu

> **Для**: Ubuntu 20.04/22.04/24.04 LTS  
> **Сложность**: Начинающий администратор  
> **Время**: 15-30 минут

## 📋 Содержание

1. [Подготовка](#-подготовка)
2. [Способ 1: Установка без Docker](#-способ-1-установка-без-docker-рекомендуется)
3. [Способ 2: Установка с Docker](#-способ-2-установка-с-docker)
4. [Настройка секретов](#-настройка-секретов)
5. [Проверка работы](#-проверка-работы)
6. [Устранение проблем](#-устранение-проблем)

---

## 🎯 Подготовка

### Требования

- **Сервер**: Ubuntu 20.04/22.04/24.04 LTS (минимум 1GB RAM, 10GB диск)
- **Доступ**: SSH доступ с правами sudo
- **Сеть**: Открытый доступ в интернет (Telegram, Google, OpenAI)
- **Токены**: 
  - Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
  - OpenAI API Key ([получить тут](https://platform.openai.com/api-keys))
  - Google Service Account JSON (инструкция ниже)

### Подключение к серверу

```bash
# С вашего компьютера
ssh username@your-server-ip

# Проверьте версию Ubuntu
lsb_release -a
```

---

## 🚀 Способ 1: Установка без Docker (рекомендуется)

### Шаг 1: Обновление системы

```bash
# Обновляем список пакетов
sudo apt update

# Обновляем систему
sudo apt upgrade -y

# Перезагружаем если были обновления ядра
sudo reboot  # подождите минуту и подключитесь снова
```

### Шаг 2: Установка Python и зависимостей

```bash
# Установка Python 3.11 (рекомендуется)
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Установка необходимых системных пакетов
sudo apt install -y git build-essential curl wget nano

# Проверка установки
python3.11 --version  # Должно показать Python 3.11.x
```

### Шаг 3: Создание пользователя для бота

```bash
# Создаем отдельного пользователя (безопаснее)
sudo useradd -m -s /bin/bash targetbot

# Задаем пароль (запомните его!)
sudo passwd targetbot

# Добавляем в группу sudo (опционально)
sudo usermod -aG sudo targetbot

# Переключаемся на пользователя
sudo su - targetbot
```

### Шаг 4: Клонирование проекта

```bash
# Клонируем репозиторий
git clone https://github.com/bivlked/target-assistant-bot.git

# Переходим в директорию
cd target-assistant-bot

# Проверяем содержимое
ls -la
```

### Шаг 5: Создание виртуального окружения

```bash
# Создаем виртуальное окружение
python3.11 -m venv .venv

# Активируем его
source .venv/bin/activate

# Обновляем pip
pip install --upgrade pip

# Устанавливаем зависимости
pip install -r requirements.txt

# Это может занять 2-5 минут
```

### Шаг 6: Настройка переменных окружения

```bash
# Копируем пример файла
cp env.example .env

# Открываем для редактирования
nano .env
```

В редакторе nano заполните следующие переменные:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather

# OpenAI
OPENAI_API_KEY=ваш_ключ_openai

# Google Sheets
GOOGLE_CREDENTIALS_PATH=./google_credentials.json

# Остальные настройки можно оставить по умолчанию
```

Сохраните файл: `Ctrl+X`, затем `Y`, затем `Enter`

### Шаг 7: Настройка Google Service Account

1. Создайте файл для credentials:
```bash
nano google_credentials.json
```

2. Вставьте содержимое вашего Service Account JSON (получение описано в разделе [Настройка секретов](#-настройка-секретов))

3. Сохраните файл

4. Установите правильные права:
```bash
chmod 600 google_credentials.json
```

### Шаг 8: Первый запуск для проверки

```bash
# Убедитесь что виртуальное окружение активно
source .venv/bin/activate

# Запустите бота
python main.py
```

Если всё настроено правильно, вы увидите:
```
INFO     | Bot started successfully!
INFO     | Scheduler started
```

Проверьте бота в Telegram - отправьте ему `/start`

Остановите бота: `Ctrl+C`

### Шаг 9: Настройка автозапуска через systemd

```bash
# Выйдите из пользователя targetbot
exit

# Создайте файл службы
sudo nano /etc/systemd/system/targetbot.service
```

Вставьте следующее содержимое:

```ini
[Unit]
Description=Target Assistant Telegram Bot
After=network.target

[Service]
Type=simple
User=targetbot
WorkingDirectory=/home/targetbot/target-assistant-bot
Environment="PATH=/home/targetbot/target-assistant-bot/.venv/bin"
ExecStart=/home/targetbot/target-assistant-bot/.venv/bin/python main.py
Restart=always
RestartSec=10

# Логирование
StandardOutput=journal
StandardError=journal

# Безопасность
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Сохраните файл и активируйте службу:

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable targetbot.service

# Запуск службы
sudo systemctl start targetbot.service

# Проверка статуса
sudo systemctl status targetbot.service
```

### Шаг 10: Настройка логов

```bash
# Просмотр логов
sudo journalctl -u targetbot.service -f

# Последние 100 строк
sudo journalctl -u targetbot.service -n 100

# Логи за сегодня
sudo journalctl -u targetbot.service --since today
```

---

## 🐳 Способ 2: Установка с Docker

### Шаг 1: Установка Docker

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Добавление GPG ключа Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавление репозитория Docker
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Применение изменений группы
newgrp docker

# Проверка установки
docker --version
docker compose version
```

### Шаг 2: Клонирование проекта

```bash
# Создаем директорию для проектов
mkdir -p ~/projects
cd ~/projects

# Клонируем репозиторий
git clone https://github.com/bivlked/target-assistant-bot.git
cd target-assistant-bot
```

### Шаг 3: Настройка переменных окружения

```bash
# Копируем пример
cp env.example .env

# Редактируем
nano .env
```

Заполните переменные как в способе 1.

### Шаг 4: Настройка Google credentials

```bash
# Создаем файл
nano google_credentials.json

# Вставляем содержимое Service Account JSON
# Сохраняем: Ctrl+X, Y, Enter

# Права доступа
chmod 600 google_credentials.json
```

### Шаг 5: Запуск через Docker Compose

```bash
# Сборка и запуск в фоновом режиме
docker compose up -d --build

# Просмотр логов
docker compose logs -f

# Остановка (Ctrl+C для выхода из логов)
docker compose stop

# Полная остановка и удаление контейнеров
docker compose down
```

### Шаг 6: Автозапуск Docker контейнера

Docker контейнеры с `restart: always` автоматически запускаются при старте системы.

Проверьте docker-compose.yml:
```yaml
services:
  bot:
    restart: always  # Эта строка обеспечивает автозапуск
```

---

## 🔐 Настройка секретов

### Получение Telegram Bot Token

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Придумайте имя бота (например: "My Target Assistant")
4. Придумайте username бота (должен заканчиваться на `bot`, например: `my_target_assistant_bot`)
5. Скопируйте полученный токен

### Получение OpenAI API Key

1. Зарегистрируйтесь на [OpenAI](https://platform.openai.com/)
2. Перейдите в [API Keys](https://platform.openai.com/api-keys)
3. Нажмите "Create new secret key"
4. Скопируйте ключ (он показывается только один раз!)

### Создание Google Service Account

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите Google Sheets API:
   - В меню выберите "APIs & Services" → "Library"
   - Найдите "Google Sheets API"
   - Нажмите "Enable"
4. Создайте Service Account:
   - "APIs & Services" → "Credentials"
   - "Create Credentials" → "Service Account"
   - Заполните имя (например: "targetbot-sheets")
   - Нажмите "Create and Continue"
   - Пропустите назначение ролей
   - Нажмите "Done"
5. Создайте ключ:
   - Кликните на созданный Service Account
   - Вкладка "Keys" → "Add Key" → "Create new key"
   - Выберите "JSON"
   - Файл автоматически скачается
6. Это и есть ваш `google_credentials.json`

---

## ✅ Проверка работы

### Базовая проверка

1. Откройте Telegram
2. Найдите вашего бота по username
3. Отправьте команды:
   - `/start` - должен поприветствовать
   - `/help` - покажет список команд
   - `/setgoal` - начнет диалог установки цели

### Проверка логов

**Для systemd:**
```bash
sudo journalctl -u targetbot.service -f
```

**Для Docker:**
```bash
docker compose logs -f
```

### Проверка процессов

**Для systemd:**
```bash
# Статус службы
sudo systemctl status targetbot

# Процессы Python
ps aux | grep python
```

**Для Docker:**
```bash
# Запущенные контейнеры
docker ps

# Статистика контейнера
docker stats
```

---

## 🔧 Устранение проблем

### Бот не отвечает

1. **Проверьте токен**:
   ```bash
   grep TELEGRAM_BOT_TOKEN .env
   ```

2. **Проверьте доступ к Telegram API**:
   ```bash
   curl -s https://api.telegram.org/bot<YOUR_TOKEN>/getMe
   ```

3. **Проверьте файрвол**:
   ```bash
   sudo ufw status
   # Если активен, разрешите исходящие соединения
   sudo ufw allow out 443/tcp
   sudo ufw allow out 80/tcp
   ```

### Ошибка Google Sheets

1. **Проверьте путь к файлу**:
   ```bash
   ls -la google_credentials.json
   ```

2. **Проверьте права**:
   ```bash
   chmod 600 google_credentials.json
   ```

3. **Проверьте валидность JSON**:
   ```bash
   python3 -m json.tool google_credentials.json
   ```

### Ошибка OpenAI

1. **Проверьте ключ**:
   ```bash
   grep OPENAI_API_KEY .env
   ```

2. **Проверьте баланс**: Зайдите в [billing](https://platform.openai.com/account/billing)

### Бот падает с ошибкой event loop

1. **Проверьте версию Python**:
   ```bash
   python3 --version
   # Рекомендуется 3.11 или 3.12
   ```

2. **Обновите зависимости**:
   ```bash
   source .venv/bin/activate
   pip install -U -r requirements.txt
   ```

### Полезные команды

```bash
# Перезапуск бота (systemd)
sudo systemctl restart targetbot

# Перезапуск бота (Docker)
docker compose restart

# Просмотр использования ресурсов
htop  # установите через: sudo apt install htop

# Проверка места на диске
df -h

# Очистка логов Docker
docker system prune -a
```

---

## 🚀 Обновление бота

### Для установки без Docker

```bash
# Переключитесь на пользователя бота
sudo su - targetbot
cd target-assistant-bot

# Сохраните важные файлы
cp .env .env.backup
cp google_credentials.json google_credentials.json.backup

# Получите обновления
git pull origin main

# Обновите зависимости
source .venv/bin/activate
pip install -U -r requirements.txt

# Перезапустите службу
exit  # выйти из пользователя targetbot
sudo systemctl restart targetbot
```

### Для Docker

```bash
cd ~/projects/target-assistant-bot

# Сохраните важные файлы
cp .env .env.backup
cp google_credentials.json google_credentials.json.backup

# Получите обновления
git pull origin main

# Пересоберите и запустите
docker compose down
docker compose up -d --build
```

---

## 📞 Поддержка

Если у вас возникли проблемы:

1. Проверьте [Issues](https://github.com/bivlked/target-assistant-bot/issues) на GitHub
2. Создайте новый Issue с описанием проблемы и логами
3. Приложите вывод команд:
   ```bash
   # Версия системы
   lsb_release -a
   
   # Версия Python
   python3 --version
   
   # Логи (последние 100 строк)
   sudo journalctl -u targetbot -n 100 --no-pager
   ```

---

💡 **Совет**: Сделайте снимок (snapshot) сервера после успешной настройки, чтобы можно было быстро восстановиться в случае проблем. 