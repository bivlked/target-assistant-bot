---
language: ru
type: api
audience: developer
difficulty: intermediate
last_updated: YYYY-MM-DD
english_version: [path_to_english_version]
russian_version: [path_to_russian_version]
---

# 🔌 API Справочник: [API_NAME]

> **Версия API**: v[VERSION]  
> **Последнее обновление**: [DATE]  
> **Статус**: ✅ Стабильный | 🔄 В разработке | ⚠️ Устаревший

## 📋 Обзор

[Краткое описание API - назначение, основные возможности]

**Base URL**: `https://api.example.com/v1`

## 🔐 Аутентификация

```http
Authorization: Bearer [YOUR_TOKEN]
Content-Type: application/json
```

## 📚 Endpoints

### 🎯 [ENDPOINT_CATEGORY]

#### `GET /api/[endpoint]`

**Описание**: [Что делает этот endpoint]

**Параметры:**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `param1` | string | Да | Описание параметра |
| `param2` | integer | Нет | Описание параметра |

**Пример запроса:**

```bash
curl -X GET "https://api.example.com/v1/endpoint" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Пример ответа:**

```json
{
  "status": "success",
  "data": {
    "id": 123,
    "name": "Пример",
    "created_at": "2025-06-10T14:00:00Z"
  },
  "meta": {
    "total": 1,
    "page": 1
  }
}
```

**Коды ответов:**

| Код | Описание |
|-----|----------|
| 200 | Успешный запрос |
| 400 | Неверные параметры |
| 401 | Не авторизован |
| 404 | Ресурс не найден |
| 500 | Внутренняя ошибка сервера |

#### `POST /api/[endpoint]`

**Описание**: [Что делает этот endpoint]

**Тело запроса:**

```json
{
  "field1": "string",
  "field2": 123,
  "field3": true
}
```

**Схема:**

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `field1` | string | Да | Описание поля |
| `field2` | integer | Нет | Описание поля |
| `field3` | boolean | Нет | Описание поля |

**Пример запроса:**

```bash
curl -X POST "https://api.example.com/v1/endpoint" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "field1": "значение",
    "field2": 123
  }'
```

## 🔧 Обработка ошибок

### Стандартный формат ошибки:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Описание ошибки",
    "details": {
      "field": "Дополнительная информация"
    }
  }
}
```

### Распространенные ошибки:

| Код ошибки | Описание | Решение |
|------------|----------|---------|
| `INVALID_TOKEN` | Недействительный токен | Проверьте токен аутентификации |
| `MISSING_FIELD` | Отсутствует обязательное поле | Добавьте все обязательные поля |
| `RATE_LIMIT` | Превышен лимит запросов | Уменьшите частоту запросов |

## 💡 Примеры использования

### Пример 1: [USE_CASE_NAME]

```python
import requests

headers = {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Content-Type': 'application/json'
}

response = requests.get(
    'https://api.example.com/v1/endpoint',
    headers=headers
)

data = response.json()
print(f"Получено {len(data['data'])} элементов")
```

### Пример 2: [USE_CASE_NAME]

```javascript
const response = await fetch('https://api.example.com/v1/endpoint', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    field1: 'значение',
    field2: 123
  })
});

const data = await response.json();
console.log('Результат:', data);
```

## 📊 Лимиты и ограничения

| Ограничение | Значение |
|-------------|----------|
| Запросов в минуту | 1000 |
| Размер запроса | 10 MB |
| Время ожидания | 30 секунд |

## 🧪 Тестирование API

### Postman Collection

[Ссылка на Postman коллекцию](POSTMAN_COLLECTION_URL)

### Swagger/OpenAPI

[Ссылка на Swagger UI](SWAGGER_URL)

## 📚 SDK и библиотеки

- **Python**: [`package-name`](PYPI_URL)
- **JavaScript**: [`package-name`](NPM_URL)
- **PHP**: [`package-name`](PACKAGIST_URL)

---

**🔗 Навигация по API:**
- 🏠 [API Главная](../api/README.md)
- 📖 [Руководство по интеграции](integration-guide.md)
- 🔧 [Решение проблем](troubleshooting.md)

---

**📝 Обратная связь:**  
Нашли ошибку в документации? [Создайте issue](../../issues/new) или отправьте Pull Request. 