# Collections API Documentation

## Базовая информация
- **Base URL**: `http://localhost:5000`
- **Content-Type**: `application/json`
- **Аутентификация**: Session-based через OAuth (Google/Apple)
- **Безопасность**: Rate limiting, CSRF protection, audit logging
- **Версия API**: v1

## Безопасность
- **Rate Limiting**: 100 запросов в час для незарегистрированных, 1000 для зарегистрированных
- **CSRF Protection**: Включен для всех POST/PUT/DELETE запросов
- **Audit Logging**: Все действия логируются для безопасности
- **File Upload Security**: Проверка типов файлов, размеров, сканирование на вредоносное ПО

## Статус коды
- `200` - Успешный запрос
- `201` - Ресурс создан
- `400` - Неверный запрос
- `401` - Не авторизован
- `403` - Доступ запрещен
- `404` - Ресурс не найден
- `429` - Превышен лимит запросов
- `500` - Внутренняя ошибка сервера

---

## Аутентификация

### POST /auth/login/google
Авторизация через Google OAuth

**Параметры запроса:**
```json
{
  "code": "authorization_code_from_google"
}
```

**Ответ:**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "avatar_url": "https://example.com/avatar.jpg"
  }
}
```

### POST /auth/login/apple
Авторизация через Apple ID

**Параметры запроса:**
```json
{
  "id_token": "apple_id_token",
  "code": "authorization_code"
}
```

**Ответ:**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

### POST /auth/logout
Выход из системы

**Ответ:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

### GET /auth/check
Проверка статуса авторизации

**Ответ (авторизован):**
```json
{
  "authenticated": true,
  "user": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

**Ответ (не авторизован):**
```json
{
  "authenticated": false
}
```

---

## Коллекции

### GET /api/collections
Получить все коллекции текущего пользователя

**Ответ:**
```json
{
  "collections": [
    {
      "id": 1,
      "name": "My Collection",
      "description": "Collection description",
      "cover_image": "/uploads/covers/image.jpg",
      "is_public": true,
      "public_url": "abc123def456",
      "created_at": "2025-01-01T12:00:00Z",
      "updated_at": "2025-01-01T12:00:00Z",
      "items_count": 5,
      "custom_fields": [
        {
          "name": "Brand",
          "type": "text",
          "required": true
        }
      ]
    }
  ]
}
```

### GET /api/collections/{id}
Получить конкретную коллекцию

**Параметры URL:**
- `id` (integer) - ID коллекции

**Ответ:**
```json
{
  "id": 1,
  "name": "My Collection",
  "description": "Collection description",
  "cover_image": "/uploads/covers/image.jpg",
  "is_public": true,
  "public_url": "abc123def456",
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:00:00Z",
  "custom_fields": [
    {
      "name": "Brand",
      "type": "text",
      "required": true
    },
    {
      "name": "Price",
      "type": "number",
      "required": false
    }
  ],
  "items": [
    {
      "id": 1,
      "name": "Item 1",
      "image": "/uploads/items/item1.jpg",
      "custom_data": {
        "Brand": "Nike",
        "Price": 100
      },
      "created_at": "2025-01-01T12:00:00Z"
    }
  ]
}
```

### POST /api/collections
Создать новую коллекцию

**Тело запроса (multipart/form-data):**
```
name: "My New Collection"
description: "Description of the collection"
is_public: true
cover_image: (file)
custom_fields: [{"name": "Brand", "type": "text", "required": true}]
```

**Ответ:**
```json
{
  "success": true,
  "collection": {
    "id": 2,
    "name": "My New Collection",
    "description": "Description of the collection",
    "cover_image": "/uploads/covers/new_image.jpg",
    "is_public": true,
    "public_url": "xyz789abc123"
  }
}
```

### PUT /api/collections/{id}
Обновить коллекцию

**Параметры URL:**
- `id` (integer) - ID коллекции

**Тело запроса (multipart/form-data):**
```
name: "Updated Collection Name"
description: "Updated description"
is_public: false
cover_image: (file, optional)
custom_fields: [{"name": "Brand", "type": "text", "required": true}]
```

**Ответ:**
```json
{
  "success": true,
  "collection": {
    "id": 1,
    "name": "Updated Collection Name",
    "description": "Updated description",
    "is_public": false
  }
}
```

### DELETE /api/collections/{id}
Удалить коллекцию

**Параметры URL:**
- `id` (integer) - ID коллекции

**Ответ:**
```json
{
  "success": true,
  "message": "Collection deleted successfully"
}
```

### GET /public/{public_url}
Публичный просмотр коллекции

**Параметры URL:**
- `public_url` (string) - Публичный URL коллекции

**Ответ:**
```json
{
  "id": 1,
  "name": "Public Collection",
  "description": "This is a public collection",
  "cover_image": "/uploads/covers/image.jpg",
  "owner_name": "John Doe",
  "created_at": "2025-01-01T12:00:00Z",
  "custom_fields": [...],
  "items": [...]
}
```

---

## Предметы коллекций

### GET /api/collections/{collection_id}/items
Получить все предметы коллекции

**Параметры URL:**
- `collection_id` (integer) - ID коллекции

**Query параметры:**
- `page` (integer, optional) - Номер страницы (по умолчанию 1)
- `per_page` (integer, optional) - Количество на странице (по умолчанию 20)
- `sort_by` (string, optional) - Поле для сортировки
- `sort_order` (string, optional) - Порядок сортировки (asc/desc)

**Ответ:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Item 1",
      "image": "/uploads/items/item1.jpg",
      "custom_data": {
        "Brand": "Nike",
        "Price": 100,
        "Date": "2025-01-01"
      },
      "created_at": "2025-01-01T12:00:00Z",
      "updated_at": "2025-01-01T12:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5,
    "pages": 1
  }
}
```

### GET /api/items/{id}
Получить конкретный предмет

**Параметры URL:**
- `id` (integer) - ID предмета

**Ответ:**
```json
{
  "id": 1,
  "name": "Item 1",
  "image": "/uploads/items/item1.jpg",
  "custom_data": {
    "Brand": "Nike",
    "Price": 100
  },
  "collection_id": 1,
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:00:00Z"
}
```

### POST /api/collections/{collection_id}/items
Добавить предмет в коллекцию

**Параметры URL:**
- `collection_id` (integer) - ID коллекции

**Тело запроса (multipart/form-data):**
```
name: "New Item"
image: (file, optional)
custom_data: {"Brand": "Nike", "Price": 100}
```

**Ответ:**
```json
{
  "success": true,
  "item": {
    "id": 2,
    "name": "New Item",
    "image": "/uploads/items/new_item.jpg",
    "custom_data": {
      "Brand": "Nike",
      "Price": 100
    },
    "collection_id": 1
  }
}
```

### PUT /api/items/{id}
Обновить предмет

**Параметры URL:**
- `id` (integer) - ID предмета

**Тело запроса (multipart/form-data):**
```
name: "Updated Item"
image: (file, optional)
custom_data: {"Brand": "Adidas", "Price": 120}
```

**Ответ:**
```json
{
  "success": true,
  "item": {
    "id": 1,
    "name": "Updated Item",
    "custom_data": {
      "Brand": "Adidas",
      "Price": 120
    }
  }
}
```

### DELETE /api/items/{id}
Удалить предмет

**Параметры URL:**
- `id` (integer) - ID предмета

**Ответ:**
```json
{
  "success": true,
  "message": "Item deleted successfully"
}
```

---

## Пользователи

### GET /api/profile
Получить профиль текущего пользователя

**Ответ:**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "avatar_url": "https://example.com/avatar.jpg",
  "created_at": "2025-01-01T12:00:00Z",
  "collections_count": 3
}
```

### PUT /api/profile
Обновить профиль пользователя

**Тело запроса:**
```json
{
  "name": "Updated Name"
}
```

**Ответ:**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "name": "Updated Name",
    "email": "john@example.com"
  }
}
```

---

## Загрузка файлов

### POST /api/upload/image
Загрузить изображение

**Тело запроса (multipart/form-data):**
```
image: (file)
type: "cover" | "item" | "avatar"
```

**Ответ:**
```json
{
  "success": true,
  "url": "/uploads/images/filename.jpg",
  "filename": "filename.jpg"
}
```

---

## Ошибки

### Формат ошибок
Все ошибки возвращаются в следующем формате:

```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

### Коды ошибок
- `UNAUTHORIZED` - Пользователь не авторизован
- `FORBIDDEN` - Недостаточно прав доступа
- `NOT_FOUND` - Ресурс не найден
- `VALIDATION_ERROR` - Ошибка валидации данных
- `UPLOAD_ERROR` - Ошибка загрузки файла
- `DATABASE_ERROR` - Ошибка базы данных
- `OAUTH_ERROR` - Ошибка OAuth авторизации

### Примеры ошибок

**401 Unauthorized:**
```json
{
  "success": false,
  "error": "Authentication required",
  "code": "UNAUTHORIZED"
}
```

**400 Validation Error:**
```json
{
  "success": false,
  "error": "Collection name is required",
  "code": "VALIDATION_ERROR",
  "details": {
    "field": "name",
    "message": "This field is required"
  }
}
```

**404 Not Found:**
```json
{
  "success": false,
  "error": "Collection not found",
  "code": "NOT_FOUND"
}
```

---

## Дополнительные возможности

### Фильтрация коллекций
GET /api/collections поддерживает следующие query параметры:
- `search` - поиск по названию и описанию
- `is_public` - фильтр по публичности (true/false)
- `sort_by` - сортировка (name, created_at, updated_at)
- `sort_order` - порядок (asc, desc)

### Фильтрация предметов
GET /api/collections/{id}/items поддерживает:
- `search` - поиск по названию предмета
- `custom_field_name` - фильтр по кастомному полю
- `date_from`, `date_to` - фильтр по дате создания

---

## Административные endpoints

### GET /admin/users
Получить список всех пользователей (только для администраторов)

**Требования**: Роль администратора

**Query параметры:**
- `page` (integer, optional) - Номер страницы
- `per_page` (integer, optional) - Количество на странице
- `search` (string, optional) - Поиск по email/имени
- `is_admin` (boolean, optional) - Фильтр по роли

**Ответ:**
```json
{
  "users": [
    {
      "id": 1,
      "email": "user@example.com",
      "name": "User Name",
      "is_admin": false,
      "is_active": true,
      "created_at": "2025-01-01T12:00:00Z",
      "last_login": "2025-01-02T12:00:00Z",
      "collections_count": 5
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 50,
    "pages": 3
  }
}
```

### PUT /admin/users/{id}/status
Изменить статус пользователя

**Параметры URL:**
- `id` (integer) - ID пользователя

**Тело запроса:**
```json
{
  "is_active": false,
  "reason": "Нарушение правил сообщества"
}
```

### GET /admin/audit-logs
Получить журнал аудита

**Query параметры:**
- `page` (integer, optional) - Номер страницы
- `user_id` (integer, optional) - Фильтр по пользователю
- `action` (string, optional) - Фильтр по действию
- `resource_type` (string, optional) - Фильтр по типу ресурса
- `date_from` (string, optional) - Дата начала (ISO format)
- `date_to` (string, optional) - Дата окончания (ISO format)

**Ответ:**
```json
{
  "logs": [
    {
      "id": 1,
      "user_id": 1,
      "action": "COLLECTION_CREATE",
      "resource_type": "COLLECTION",
      "resource_id": 5,
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "details": {
        "collection_name": "My New Collection"
      },
      "created_at": "2025-01-01T12:00:00Z"
    }
  ],
  "pagination": {...}
}
```

### GET /admin/stats
Получить статистику системы

**Ответ:**
```json
{
  "stats": {
    "users": {
      "total": 1500,
      "active": 1200,
      "new_this_month": 150
    },
    "collections": {
      "total": 5000,
      "public": 2500,
      "private": 2500
    },
    "items": {
      "total": 25000
    },
    "storage": {
      "total_size_mb": 2048,
      "files_count": 8500
    },
    "rate_limits": {
      "current_hour": 1250,
      "blocked_requests": 15
    }
  }
}
```

---

## Системные endpoints

### GET /health
Проверка работоспособности системы

**Ответ:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T12:00:00Z",
  "services": {
    "database": "ok",
    "uploads": "ok",
    "storage": "ok"
  },
  "version": "1.0.0"
}
```

### GET /metrics
Метрики системы (для мониторинга)

**Ответ:**
```json
{
  "requests_total": 10000,
  "requests_per_minute": 150,
  "response_time_avg_ms": 45,
  "active_sessions": 250,
  "upload_rate_mb_per_hour": 500,
  "database_connections": 5
}
```

---

## Расширенные возможности загрузки

### POST /api/upload/image
Загрузить изображение с автоматической обработкой

**Тело запроса (multipart/form-data):**
```
image: (file)
type: "cover" | "item" | "avatar"
resize: "auto" | "manual"
sizes: ["original", "medium", "thumbnail"] (optional)
quality: 85 (optional, 1-100)
```

**Ответ:**
```json
{
  "success": true,
  "files": {
    "original": {
      "url": "/uploads/original/filename.jpg",
      "size": 2048000,
      "dimensions": "1920x1080"
    },
    "medium": {
      "url": "/uploads/medium/filename.jpg", 
      "size": 512000,
      "dimensions": "800x450"
    },
    "thumbnail": {
      "url": "/uploads/thumbnail/filename.jpg",
      "size": 64000,
      "dimensions": "200x112"
    }
  },
  "metadata": {
    "original_name": "photo.jpg",
    "mime_type": "image/jpeg",
    "upload_time": "2025-01-01T12:00:00Z"
  }
}
```

### DELETE /api/uploads/{filename}
Удалить загруженный файл

**Параметры URL:**
- `filename` (string) - Имя файла

**Ответ:**
```json
{
  "success": true,
  "message": "File deleted successfully"
}
```

---

## Безопасность и ошибки

### Rate Limiting Headers
Все ответы включают заголовки rate limiting:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 3600
```

### Коды ошибок безопасности
- `RATE_LIMIT_EXCEEDED` - Превышен лимит запросов
- `INVALID_FILE_TYPE` - Недопустимый тип файла
- `FILE_TOO_LARGE` - Файл слишком большой
- `MALICIOUS_FILE_DETECTED` - Обнаружен вредоносный файл
- `CSRF_TOKEN_MISSING` - Отсутствует CSRF токен
- `CSRF_TOKEN_INVALID` - Недействительный CSRF токен
- `ADMIN_ACCESS_REQUIRED` - Требуются права администратора

### Аудит действий
Следующие действия автоматически логируются:
- `USER_LOGIN` / `USER_LOGOUT`
- `COLLECTION_CREATE` / `COLLECTION_UPDATE` / `COLLECTION_DELETE`
- `ITEM_CREATE` / `ITEM_UPDATE` / `ITEM_DELETE`
- `FILE_UPLOAD` / `FILE_DELETE`
- `ADMIN_ACTION`
- `SECURITY_VIOLATION`
- `RATE_LIMIT_EXCEEDED`

### Примеры ошибок безопасности

**429 Rate Limit Exceeded:**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "details": {
    "limit": 1000,
    "window": 3600,
    "reset_time": "2025-01-01T13:00:00Z"
  }
}
```

**403 Admin Access Required:**
```json
{
  "success": false,
  "error": "Administrator access required",
  "code": "ADMIN_ACCESS_REQUIRED"
}
```

---

## CLI команды

### Управление базой данных
```bash
# Создать таблицы
flask create-db

# Удалить все таблицы
flask drop-db

# Пересоздать базу данных
flask reset-db
```

### Управление пользователями
```bash
# Создать администратора
flask create-admin

# Интерактивное создание администратора
python run.py create-admin
```

### Безопасность и мониторинг
```bash
# Проверка безопасности
flask security-check
python run.py security-check

# Очистка старых логов
flask cleanup-logs
python run.py cleanup-logs
```

### Flask shell
```bash
# Запуск интерактивной оболочки
flask shell

# Доступные объекты в shell:
# - db, User, Collection, Item, AuditLog
# - AuditAction, ResourceType, AuditLogger
# - get_rate_limit_stats()
```

---

## Мониторинг и метрики

### Проверка статуса rate limiting
```python
from app.utils.rate_limiter import get_rate_limit_stats

# В Flask shell
stats = get_rate_limit_stats()
print(stats)
```

### Анализ журнала аудита
```python
from app.models.audit_log import AuditLog, AuditAction
from app.utils.logger import AuditLogger

# Последние действия пользователя
recent_actions = AuditLog.query.filter_by(user_id=1).order_by(AuditLog.created_at.desc()).limit(10).all()

# Статистика по действиям
action_stats = db.session.query(AuditLog.action, db.func.count()).group_by(AuditLog.action).all()
```

---

## Производительность

### Оптимизация изображений
- Автоматическое сжатие при загрузке
- Генерация thumbnail'ов разных размеров
- Прогрессивное JPEG для больших изображений
- WebP формат для поддерживающих браузеров

### Кэширование
- Статические файлы кэшируются на 1 год
- API ответы кэшируются на основе ETag
- Изображения кэшируются в CDN (если настроен)

### Лимиты
- Максимальный размер изображения: 10MB
- Максимальное количество коллекций на пользователя: 100
- Максимальное количество предметов в коллекции: 1000
- Максимальная длина названия коллекции: 255 символов
- Максимальная длина описания: 2000 символов
- Максимальное количество кастомных полей: 20