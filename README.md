# Руководство по развертыванию Collections с обеспечением безопасности

## Этап 10: Логирование и безопасность

Этот документ описывает реализованные функции безопасности и инструкции по их настройке.

## 🛡️ Реализованные функции безопасности

### 1. Система логирования действий пользователей

#### Функции:
- Логирование всех действий пользователей (создание, изменение, удаление, просмотр)
- Запись IP-адресов и User-Agent
- Централизованное логирование через `AuditLogger`
- Автоматические триггеры базы данных для критических операций

#### Логируемые события:
- **Аутентификация**: вход, выход, неудачные попытки входа
- **Пользователи**: создание, обновление, блокировка
- **Коллекции**: создание, просмотр, изменение, удаление, публикация
- **Предметы**: создание, просмотр, изменение, удаление
- **Система**: запуск приложения, ошибки, загрузка файлов

### 2. Rate Limiting

#### Реализованные лимиты:

| Операция | Лимит | Окно времени | Блокировка |
|----------|-------|--------------|------------|
| Аутентификация | 5 попыток | 15 минут | 30 минут |
| Регистрация | 3 попытки | 1 час | 1 час |
| API чтение | 1000 запросов | 1 час | - |
| API запись | 100 запросов | 1 час | - |
| API удаление | 50 запросов | 1 час | - |
| Загрузка файлов | 20 загрузок | 1 час | - |
| Публичный просмотр | 2000 просмотров | 1 час | - |

#### Функции:
- Адаптивные лимиты в зависимости от типа операции
- Приоритет user_id над IP-адресом для аутентифицированных пользователей
- Автоматическая очистка старых данных
- Информативные заголовки HTTP с информацией о лимитах

### 3. Валидация входных данных

#### Валидация файлов:
- Проверка расширений файлов (png, jpg, jpeg, gif, webp)
- Проверка MIME-типов
- Проверка размера файлов (до 10MB)
- Проверка размеров изображений (до 4000x4000 пикселей)
- Проверка целостности изображений
- Генерация безопасных имен файлов

#### Валидация текстовых данных:
- Очистка от HTML тегов
- Проверка длины полей
- Валидация email адресов
- Проверка на потенциально опасные символы
- Валидация кастомных полей коллекций

### 4. Security Headers

#### Настроенные заголовки:
```http
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://apis.google.com; ...
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Strict-Transport-Security: max-age=31536000; includeSubDomains (только HTTPS)
```

## 📋 Инструкции по развертыванию

### 1. Подготовка базы данных

Если у вас уже есть существующая база данных:

```bash
# Выполните миграцию для добавления таблицы логирования
sqlite3 collections.db < backend/migrations/add_audit_log_table.sql
```

Для новой установки:
```bash
cd backend
python run.py create-db
```

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# Основные настройки
FLASK_ENV=production
SECRET_KEY=your-very-long-random-secret-key-here
HOST=0.0.0.0
PORT=5000

# Безопасность
FORCE_HTTPS=true
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax

# База данных
DATABASE_URL=sqlite:///collections.db

# OAuth настройки
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
APPLE_CLIENT_ID=your-apple-client-id
APPLE_TEAM_ID=your-apple-team-id
APPLE_KEY_ID=your-apple-key-id
APPLE_PRIVATE_KEY_PATH=path/to/apple/private/key.p8

# Загрузка файлов
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=52428800  # 50MB
```

### 3. Настройка директорий и прав доступа

```bash
# Создание директорий
mkdir -p uploads/{original,medium,thumbnail}
mkdir -p logs

# Установка безопасных прав доступа
chmod 755 uploads
chmod 755 uploads/*
chmod 750 logs

# Создание .htaccess для защиты папки uploads (Apache)
cat > uploads/.htaccess << 'EOF'
# Запрещаем выполнение PHP и других скриптов
php_flag engine off
AddType text/plain .php .php3 .phtml .pht .pl .py .jsp .asp .sh .cgi

# Разрешаем только изображения
<FilesMatch "\.(jpg|jpeg|png|gif|webp)$">
    Order Allow,Deny
    Allow from all
</FilesMatch>
EOF
```

### 4. Установка зависимостей

```bash
cd backend
pip install -r requirements.txt

# Дополнительные зависимости для безопасности
pip install python-magic  # Для проверки MIME-типов файлов
```

### 5. Создание первого администратора

```bash
python run.py create-admin
```

### 6. Проверка безопасности

```bash
python run.py security-check
```

### 7. Настройка веб-сервера (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL настройки
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=1r/s;

    # Проксирование к Flask приложению
    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Более строгие лимиты для аутентификации
    location /auth/ {
        limit_req zone=auth burst=5 nodelay;
        
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Статические файлы
    location /api/files/ {
        alias /path/to/uploads/;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }
}
```

## 🔧 Администрирование

### Просмотр логов безопасности

```python
# В Flask shell
from app.models.audit_log import AuditLog
from app.utils.logger import AuditLogger

# Последние 100 действий
logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
for log in logs:
    print(f"{log.timestamp}: {log.action} by user {log.user_id}")

# Активность конкретного пользователя
user_logs = AuditLogger.get_user_activity(user_id=1, limit=50)

# Активность по ресурсу
resource_logs = AuditLogger.get_resource_activity('COLLECTION', resource_id=1)
```

### Мониторинг rate limiting

```python
from app.utils.rate_limiter import get_rate_limit_stats

# Статистика по rate limiting
stats = get_rate_limit_stats()
print(f"Active keys: {stats['active_keys']}")
print(f"Blocked keys: {stats['blocked_keys']}")
print(f"Total requests: {stats['total_requests']}")
```

### Очистка старых данных

```bash
# Очистка старых логов
python run.py cleanup-logs

# Очистка данных rate limiter (автоматически каждые 24 часа)
```

## 🚨 Мониторинг и алерты

### Критические события для мониторинга

1. **Подозрительная активность:**
   - Множественные неудачные попытки входа с одного IP
   - Превышение rate limits
   - Попытки доступа к несуществующим ресурсам
   - Загрузка подозрительных файлов

2. **Системные события:**
   - Ошибки базы данных
   - Превышение лимитов дискового пространства
   - Недоступность внешних сервисов (OAuth)

### Настройка алертов

```python
# Пример скрипта для мониторинга подозрительной активности
from app.models.audit_log import AuditLog
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MimeText

def check_suspicious_activity():
    # Проверяем неудачные попытки входа за последний час
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    failed_logins = AuditLog.query.filter(
        AuditLog.action == 'LOGIN_FAILED',
        AuditLog.timestamp >= one_hour_ago
    ).all()
    
    # Группируем по IP адресам
    ip_counts = {}
    for log in failed_logins:
        ip = log.ip_address
        ip_counts[ip] = ip_counts.get(ip, 0) + 1
    
    # Отправляем алерт если с одного IP больше 10 неудачных попыток
    for ip, count in ip_counts.items():
        if count > 10:
            send_security_alert(f"Suspicious activity from IP {ip}: {count} failed login attempts")

def send_security_alert(message):
    # Отправка уведомления администратору
    pass
```

## 📊 Метрики производительности

### Рекомендуемые метрики для мониторинга

1. **Производительность:**
   - Время ответа API endpoints
   - Использование CPU и памяти
   - Количество активных соединений

2. **Безопасность:**
   - Количество заблокированных IP адресов
   - Частота срабатывания rate limits
   - Количество подозрительных файлов

3. **Использование:**
   - Количество активных пользователей
   - Количество созданных коллекций
   - Объем загруженных файлов

## 🔄 Процедуры обновления

### Обновление системы безопасности

1. **Создание резервной копии:**
   ```bash
   # Резервная копия базы данных
   cp collections.db collections.db.backup.$(date +%Y%m%d_%H%M%S)
   
   # Резервная копия файлов
   tar -czf uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/
   ```

2. **Тестирование на staging окружении:**
   - Развертывание на тестовом сервере
   - Проверка всех функций безопасности
   - Тестирование производительности

3. **Развертывание на production:**
   - Обновление кода
   - Выполнение миграций
   - Перезапуск сервисов
   - Проверка логов

## ⚡ Оптимизация производительности

### Настройки базы данных

```sql
-- Оптимизация SQLite для производительности
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 1000000;
PRAGMA temp_store = memory;
```

### Очистка audit_logs

```python
# Скрипт для очистки старых записей логирования
from app.models.audit_log import AuditLog
from datetime import datetime, timedelta

def cleanup_old_audit_logs(days_to_keep=90):
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    
    # Удаляем записи старше указанного количества дней
    old_logs = AuditLog.query.filter(AuditLog.timestamp < cutoff_date)
    count = old_logs.count()
    old_logs.delete()
    
    db.session.commit()
    print(f"Deleted {count} old audit log entries")
```

## 🛠️ Troubleshooting

### Часто встречающиеся проблемы

#### 1. Rate limiting блокирует легитимных пользователей

**Симптомы:** Пользователи получают ошибку 429 "Too Many Requests"

**Решение:**
```python
# Временное увеличение лимитов или сброс блокировки
from app.utils.rate_limiter import rate_limiter

# Очистка блокировок для конкретного IP
ip_key = "ip:192.168.1.100"
if ip_key in rate_limiter.blocked_until:
    del rate_limiter.blocked_until[ip_key]
    
# Или полная очистка (осторожно!)
rate_limiter.blocked_until.clear()
```

#### 2. Логи audit_logs растут слишком быстро

**Симптомы:** Быстрый рост размера базы данных

**Решение:**
- Настроить автоматическую очистку старых записей
- Архивировать важные логи в отдельное хранилище
- Оптимизировать логирование (убрать избыточные события)

#### 3. Ошибки загрузки файлов

**Симптомы:** Ошибки валидации файлов, проблемы с правами доступа

**Решение:**
```bash
# Проверка прав доступа
ls -la uploads/
chmod 755 uploads/
chmod 755 uploads/*

# Проверка места на диске
df -h

# Проверка логов загрузки
tail -f logs/uploads.log
```

#### 4. Проблемы с OAuth аутентификацией

**Симптомы:** Ошибки при входе через Google/Apple

**Решение:**
- Проверить настройки OAuth в .env файле
- Проверить redirect URLs в консолях разработчиков
- Проверить логи аутентификации

```python
# Проверка неудачных попыток аутентификации
failed_auths = AuditLog.query.filter(
    AuditLog.action == 'LOGIN_FAILED',
    AuditLog.timestamp >= datetime.utcnow() - timedelta(hours=1)
).all()

for log in failed_auths:
    print(f"Failed auth: {log.details}")
```

## 📋 Чеклист развертывания

### Перед развертыванием

- [ ] Все переменные окружения настроены
- [ ] SSL сертификаты установлены
- [ ] Настроены backup процедуры
- [ ] Проведено тестирование безопасности
- [ ] Настроен мониторинг

### После развертывания

- [ ] Проверка работы OAuth аутентификации
- [ ] Тестирование загрузки файлов
- [ ] Проверка работы rate limiting
- [ ] Тестирование создания коллекций
- [ ] Проверка логирования действий
- [ ] Тестирование публичных ссылок

### Еженедельное обслуживание

- [ ] Проверка логов безопасности
- [ ] Анализ статистики rate limiting
- [ ] Очистка старых файлов и логов
- [ ] Проверка свободного места на диске
- [ ] Обновление резервных копий

## 🔐 Дополнительные рекомендации по безопасности

### Для продакшен окружения

1. **Регулярные обновления:**
   - Обновляйте все зависимости
   - Следите за уязвимостями в безопасности
   - Используйте автоматические уведомления

2. **Мониторинг файловой системы:**
   - Настройте мониторинг изменений в критических файлах
   - Регулярно проверяйте целостность файлов
   - Используйте антивирусные решения

3. **Сетевая безопасность:**
   - Используйте firewall
   - Ограничьте доступ к административным портам
   - Настройте VPN для административного доступа

4. **Резервное копирование:**
   - Автоматические ежедневные backup
   - Тестирование восстановления из backup
   - Хранение backup в географически разных местах

## 📞 Поддержка

При возникновении проблем с безопасностью:

1. Проверьте логи в директории `logs/`
2. Используйте команду `python run.py security-check`
3. Просмотрите audit logs в базе данных
4. Проверьте статистику rate limiting

**Важно:** В случае подозрения на взлом немедленно:
- Измените все пароли и ключи
- Проанализируйте audit logs
- Обновите все зависимости
- Проведите полную проверку безопасности