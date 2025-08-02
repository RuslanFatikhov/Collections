# Collections API Documentation

## Базовая информация
- **Base URL**: `http://localhost:5000`
- **Content-Type**: `application/json`
- **Аутентификация**: Session-based через OAuth (Google/Apple)

## Статус коды
- `200` - Успешный запрос
- `201` - Ресурс создан
- `400` - Неверный запрос
- `401` - Не авторизован
- `403` - Доступ запрещен
- `404` - Ресурс не найден
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

### Лимиты
- Максимальный размер изображения: 10MB
- Поддерживаемые форматы: JPG, PNG, GIF, WEBP
- Максимальное количество кастомных полей: 20
- Максимальная длина названия коллекции: 255 символов
- Максимальная длина описания: 2000 символов