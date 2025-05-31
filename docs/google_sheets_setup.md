# 📊 Настройка Google Sheets API

<div align="center">
  <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Green%20Book.png" width="150">
  
  <h2>Пошаговая инструкция по настройке Google Sheets</h2>
  <p>Создание Service Account для работы бота с таблицами</p>
</div>

## 📋 Содержание

- [🎯 Что такое Service Account](#-что-такое-service-account)
- [📝 Шаг 1: Создание проекта в Google Cloud](#-шаг-1-создание-проекта-в-google-cloud)
- [🔑 Шаг 2: Создание Service Account](#-шаг-2-создание-service-account)
- [📄 Шаг 3: Создание ключа доступа](#-шаг-3-создание-ключа-доступа)
- [⚙️ Шаг 4: Включение Google Sheets API](#️-шаг-4-включение-google-sheets-api)
- [🛠️ Шаг 5: Настройка в боте](#️-шаг-5-настройка-в-боте)
- [❓ Частые проблемы](#-частые-проблемы)

---

## 🎯 Что такое Service Account

**Service Account** - это специальный тип Google аккаунта для приложений. Он позволяет боту:
- ✅ Создавать Google таблицы
- ✅ Читать и записывать данные
- ✅ Работать без вашего участия
- ✅ Безопасно хранить данные

> 💡 **Важно**: Service Account работает от имени бота, а не от вашего личного аккаунта

---

## 📝 Шаг 1: Создание проекта в Google Cloud

### 1.1 Перейдите в Google Cloud Console

🔗 [https://console.cloud.google.com/](https://console.cloud.google.com/)

> Если у вас нет аккаунта Google Cloud, система предложит создать его бесплатно

### 1.2 Создайте новый проект

1. Нажмите на выпадающее меню проектов сверху
2. Нажмите **"Новый проект"**

<div align="center">
  <img src="https://user-images.githubusercontent.com/placeholder/new-project.png" alt="New Project" width="600">
</div>

3. Заполните форму:
   - **Название проекта**: `Target Assistant Bot`
   - **Идентификатор проекта**: оставьте автоматический
   - **Расположение**: можно оставить пустым

4. Нажмите **"Создать"**

### 1.3 Дождитесь создания проекта

Это займет 10-30 секунд. Вы увидите уведомление о готовности.

---

## 🔑 Шаг 2: Создание Service Account

### 2.1 Откройте раздел Service Accounts

1. В левом меню найдите **"IAM и администрирование"**
2. Выберите **"Сервисные аккаунты"**

Или перейдите по прямой ссылке:
🔗 [https://console.cloud.google.com/iam-admin/serviceaccounts](https://console.cloud.google.com/iam-admin/serviceaccounts)

### 2.2 Создайте новый Service Account

1. Нажмите **"+ Создать сервисный аккаунт"**
2. Заполните данные:

**Шаг 1 - Основная информация:**
- **Название**: `target-bot-sheets`
- **Идентификатор**: автоматически заполнится
- **Описание**: `Service account for Target Assistant Bot to access Google Sheets`

<div align="center">
  <img src="https://user-images.githubusercontent.com/placeholder/service-account-1.png" alt="Service Account Step 1" width="600">
</div>

3. Нажмите **"Создать и продолжить"**

**Шаг 2 - Роли (можно пропустить):**
- Нажмите **"Продолжить"** без выбора ролей

**Шаг 3 - Доступ (можно пропустить):**
- Нажмите **"Готово"**

### 2.3 Запомните email сервисного аккаунта

После создания вы увидите email вида:
```
target-bot-sheets@your-project-id.iam.gserviceaccount.com
```

> 📌 **Важно**: Сохраните этот email - он понадобится позже!

---

## 📄 Шаг 3: Создание ключа доступа

### 3.1 Откройте созданный Service Account

Кликните на email вашего сервисного аккаунта в списке

### 3.2 Создайте новый ключ

1. Перейдите на вкладку **"Ключи"**
2. Нажмите **"Добавить ключ"** → **"Создать новый ключ"**

<div align="center">
  <img src="https://user-images.githubusercontent.com/placeholder/create-key.png" alt="Create Key" width="600">
</div>

3. Выберите формат **JSON**
4. Нажмите **"Создать"**

### 3.3 Сохраните файл ключа

- Файл автоматически скачается на ваш компьютер
- Переименуйте его в `google_credentials.json`
- **ВАЖНО**: Храните этот файл в безопасности!

> ⚠️ **Безопасность**: Никогда не публикуйте этот файл в открытых источниках!

---

## ⚙️ Шаг 4: Включение Google Sheets API

### 4.1 Откройте библиотеку API

1. В левом меню выберите **"API и сервисы"** → **"Библиотека"**

Или перейдите по ссылке:
🔗 [https://console.cloud.google.com/apis/library](https://console.cloud.google.com/apis/library)

### 4.2 Найдите Google Sheets API

1. В поиске введите: `Google Sheets API`
2. Кликните на результат **Google Sheets API**

<div align="center">
  <img src="https://user-images.githubusercontent.com/placeholder/sheets-api.png" alt="Google Sheets API" width="600">
</div>

### 4.3 Включите API

1. Нажмите кнопку **"Включить"**
2. Дождитесь активации (5-10 секунд)

### 4.4 Включите Google Drive API (опционально)

Повторите те же шаги для **Google Drive API** - это даст дополнительные возможности:
- Создание папок
- Управление доступом
- Поиск файлов

---

## 🛠️ Шаг 5: Настройка в боте

### 5.1 Поместите файл credentials

1. Скопируйте `google_credentials.json` в папку с ботом
2. Убедитесь, что файл находится в корне проекта:
```
target-assistant-bot/
├── google_credentials.json  ← здесь
├── main.py
├── .env
└── ...
```

### 5.2 Настройте переменные окружения

Откройте файл `.env` и добавьте:
```env
# Google Sheets
GOOGLE_CREDENTIALS_PATH=google_credentials.json
```

### 5.3 Проверьте .gitignore

Убедитесь, что файл с ключами не попадет в Git:
```gitignore
# Google credentials
google_credentials.json
*_credentials.json
```

---

## ❓ Частые проблемы

### 🔴 Ошибка "API not enabled"

**Проблема**: API Google Sheets не включен для проекта

**Решение**:
1. Вернитесь к [Шагу 4](#️-шаг-4-включение-google-sheets-api)
2. Убедитесь, что API включен именно в вашем проекте
3. Подождите 1-2 минуты после включения

### 🔴 Ошибка "Invalid credentials"

**Проблема**: Неверный файл с ключами

**Решение**:
1. Проверьте, что файл `google_credentials.json` не поврежден
2. Убедитесь, что путь в `.env` указан правильно
3. Пересоздайте ключ, если нужно

### 🔴 Ошибка "Permission denied"

**Проблема**: У Service Account нет доступа к таблице

**Решение**:
1. Откройте созданную таблицу
2. Нажмите "Поделиться"
3. Добавьте email вашего Service Account
4. Дайте права "Редактор"

### 🔴 Квоты и лимиты

Google Sheets API имеет лимиты:
- 500 запросов в 100 секунд на пользователя
- 100 запросов в секунду на проект

Для обычного использования бота этого более чем достаточно.

---

## 🎉 Готово!

Теперь ваш бот может работать с Google Sheets! 

### Что дальше?

1. ✅ Запустите бота командой `python main.py`
2. ✅ Отправьте `/start` в Telegram
3. ✅ Создайте первую цель
4. ✅ Проверьте, что таблица создалась

### Полезные ссылки

- 📖 [Документация Google Sheets API](https://developers.google.com/sheets/api)
- 🔧 [Google Cloud Console](https://console.cloud.google.com/)
- 💬 [Поддержка бота](https://t.me/targetassistant_support)

---

<div align="center">
  <p>
    <strong>Возникли проблемы?</strong><br>
    Создайте <a href="https://github.com/bivlked/target-assistant-bot/issues/new">Issue</a> с описанием проблемы
  </p>
  
  <br>
  
  <a href="../README.md">← Вернуться к README</a> • 
  <a href="install_ubuntu_detailed.md">Полная установка →</a>
</div> 