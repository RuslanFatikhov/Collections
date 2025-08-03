# Collections

Продвинутое веб-приложение для создания и управления пользовательскими коллекциями с кастомными параметрами, системой безопасности и административной панелью.

## 🌟 Возможности

### Основной функционал
- 🔐 **Авторизация**: OAuth через Google и Apple ID
- 📋 **Коллекции**: Создание с кастомными полями (текст, число, дата, фото, чекбокс)
- 📸 **Медиа**: Загрузка и автоматическая обработка изображений
- 🌐 **Публичность**: Публичные ссылки для просмотра коллекций
- 📱 **Адаптивность**: Отзывчивый дизайн для всех устройств
- 🔍 **Поиск**: Поиск и фильтрация предметов в коллекциях

### Безопасность и мониторинг
- 🛡️ **Rate Limiting**: Защита от злоупотреблений API
- 📊 **Аудит**: Полное логирование всех действий пользователей
- 🔒 **CSRF Protection**: Защита от межсайтовой подделки запросов
- 🖼️ **Безопасность файлов**: Проверка типов и сканирование загружаемых файлов
- 👨‍💼 **Админ-панель**: Управление пользователями и мониторинг системы

### Производительность
- ⚡ **Оптимизация изображений**: Автоматическое сжатие и создание thumbnails
- 💾 **Кэширование**: Эффективное кэширование статических ресурсов
- 📈 **Метрики**: Мониторинг производительности в реальном времени

## 🛠 Технический стек

- **Backend**: Python + Flask + SQLAlchemy
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **База данных**: SQLite (разработка) / PostgreSQL (продакшн)
- **Аутентификация**: OAuth 2.0 (Google, Apple)
- **Хранение файлов**: Локальное / S3-совместимое хранилище
- **Безопасность**: Rate limiting, CSRF protection, audit logging
- **Мониторинг**: Встроенная система метрик и логирования

## 🚀 Быстрый старт

### Системные требования

- Python 3.8+
- pip
- Git
- 512MB+ свободного места на диске

### 1. Клонирование и установка

```bash
# Клонируем репозиторий
git clone <repository-url>
cd collections

# Переходим в backend
cd backend

# Устанавливаем зависимости
pip install -r requirements.txt
```

### 2. Настройка окружения

```bash
# Копируем пример конфигурации
cp ../.env.example ../.env

# Редактируем конфигурацию
nano ../.env  # или любой другой редактор
```

Минимальная конфигурация для запуска:
```bash
FLASK_ENV=development
SECRET_KEY=your-unique-secret-key-here
DATABASE_URL=sqlite:///collections.db
BASE_URL=http://localhost:5000
```

### 3. Инициализация базы данных

```bash
# Полная инициализация с тестовыми данными и администратором
python init_db.py --sample-data --admin

# Или пошагово:
python init_db.py --check-only     # Проверка конфигурации
python init_db.py                  # Создание пустой БД
python init_db.py --sample-data    # Добавление тестовых данных
python init_db.py --admin          # Создание администратора
```

### 4. Запуск приложения

```bash
python run.py
```

✅ **Готово!** Приложение доступно по адресу: http://localhost:5000

## 📁 Структура проекта

```
collections/
├── backend/                    # Flask приложение
│   ├── app/
│   │   ├── config/            # Конфигурация и OAuth
│   │   ├── controllers/       # Бизнес-логика
│   │   ├── models/           # Модели данных + аудит
│   │   ├── utils/            # Утилиты (безопасность, логирование)
│   │   └── views/            # API маршруты
│   ├── logs/                 # Файлы логов
│   ├── init_db.py           # Скрипт инициализации БД
│   ├── run.py               # Точка входа с CLI командами
│   └── requirements.txt     # Python зависимости
├── frontend/                 # Клиентская часть
│   ├── static/
│   │   ├── css/             # Стили
│   │   ├── js/              # JavaScript
│   │   └── uploads/         # Загруженные файлы
│   │       ├── original/    # Оригинальные изображения
│   │       ├── medium/      # Средние размеры
│   │       └── thumbnail/   # Миниатюры
│   └── templates/           # HTML шаблоны
├── docs/                    # Документация
├── .env.example            # Пример конфигурации
└── README.md              # Этот файл
```

## ⚙️ Конфигурация

### OAuth настройки

#### Google OAuth 2.0
1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте проект или выберите существующий
3. Включите Google+ API или People API
4. Создайте OAuth 2.0 клиент:
   - **Тип**: Web application
   - **Authorized redirect URIs**: `http://localhost:5000/auth/google/callback`
5. Добавьте в `.env`:
   ```bash
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

#### Apple Sign In
1. Перейдите в [Apple Developer Console](https://developer.apple.com/)
2. Создайте Service ID для вашего приложения
3. Настройте домены и redirect URLs: `http://localhost:5000/auth/apple/callback`
4. Создайте ключ для Sign in with Apple
5. Добавьте в `.env`:
   ```bash
   APPLE_CLIENT_ID=com.yourcompany.collections
   APPLE_CLIENT_SECRET=your-client-secret
   APPLE_KEY_ID=your-key-id
   APPLE_TEAM_ID=your-team-id
   APPLE_PRIVATE_KEY=/path/to/AuthKey_XXXXX.p8
   ```

### Продакшн конфигурация

```bash
# Режим работы
FLASK_ENV=production

# Безопасность
SECRET_KEY=super-secure-random-key-64-chars-minimum
FORCE_HTTPS=true
SESSION_COOKIE_SAMESITE=Strict

# База данных
DATABASE_URL=postgresql://user:password@localhost:5432/collections

# S3 хранилище
USE_S3=true
S3_BUCKET=collections-storage
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_ENDPOINT=https://s3.timeweb.com
```

## 🔧 Управление приложением

### CLI команды

```bash
# Управление базой данных
python run.py create-db         # Создать таблицы
python run.py drop-db          # Удалить все таблицы
python run.py reset-db         # Пересоздать БД

# Управление пользователями
python run.py create-admin     # Создать администратора

# Безопасность и мониторинг
python run.py security-check   # Проверка безопасности
python run.py cleanup-logs     # Очистка старых логов

# Flask shell с предзагруженными объектами
flask shell
```

### Скрипт инициализации

```bash
# Проверка системы
python init_db.py --check-only

# Проверка безопасности
python init_db.py --security-check

# Управление данными
python init_db.py --force              # Пересоздать БД
python init_db.py --sample-data        # Добавить тестовые данные
python init_db.py --cleanup           # Очистить тестовые данные
python init_db.py --stats             # Статистика БД

# Создание администратора
python init_db.py --admin
```

## 📊 Мониторинг и администрирование

### Административная панель
После входа под администратором доступны:
- 👥 **Управление пользователями**: просмотр, блокировка, назначение ролей
- 📋 **Мониторинг коллекций**: модерация содержимого
- 📊 **Аналитика**: статистика использования системы
- 🛡️ **Журнал аудита**: логи всех действий пользователей
- ⚡ **Метрики производительности**: rate limiting, время ответа API

### Логирование
Система создает следующие типы логов:
- `app.log` - основной лог приложения
- `uploads.log` - логи загрузки файлов  
- `security.log` - события безопасности
- `audit.log` - аудит действий пользователей

### Метрики безопасности
- Rate limiting с настраиваемыми лимитами
- Аудит всех CRUD операций
- Логирование подозрительной активности
- Защита от загрузки вредоносных файлов

## 🧪 Тестовые данные

При использовании `--sample-data` создается:

**Тестовый пользователь:**
- Email: `test@example.com`
- Имя: Тестовый пользователь

**Коллекции:**
1. **Коллекция кроссовок** (публичная)
   - Кастомные поля: Бренд, Размер, Цена, Дата покупки, Любимые
   - Предметы: Nike Air Max 90, Adidas Ultraboost 22, Converse Chuck Taylor

2. **Коллекция книг** (приватная)
   - Кастомные поля: Автор, Жанр, Год издания, Рейтинг, Прочитано
   - Предметы: "1984", "Мастер и Маргарита"

3. **Винтажные игрушки** (публичная)
   - Кастомные поля: Производитель, Год выпуска, Состояние, Цена покупки, Редкая
   - Предметы: Трансформер Оптимус Прайм

## 📚 API документация

Полная документация API доступна в [`docs/api_documentation.md`](docs/api_documentation.md).

### Основные endpoints

**Коллекции:**
- `GET /api/collections` - Список коллекций пользователя
- `POST /api/collections` - Создать коллекцию
- `GET /api/collections/{id}` - Получить коллекцию
- `PUT /api/collections/{id}` - Обновить коллекцию
- `DELETE /api/collections/{id}` - Удалить коллекцию

**Предметы:**
- `GET /api/collections/{id}/items` - Предметы коллекции
- `POST /api/collections/{id}/items` - Добавить предмет
- `PUT /api/items/{id}` - Обновить предмет
- `DELETE /api/items/{id}` - Удалить предмет

**Администрирование:**
- `GET /admin/users` - Список пользователей
- `GET /admin/audit-logs` - Журнал аудита
- `GET /admin/stats` - Статистика системы

**Публичный доступ:**
- `GET /public/{public_url}` - Просмотр публичной коллекции

## 🐛 Устранение проблем

### Проблемы с зависимостями
```bash
# Обновить pip
python -m pip install --upgrade pip

# Переустановить зависимости
pip install -r requirements.txt --force-reinstall

# Проверить установку
python init_db.py --check-only
```

### Проблемы с базой данных
```bash
# Проверить подключение
python -c "from app import create_app, db; app=create_app(); app.app_context().push(); db.session.execute(db.text('SELECT 1'))"

# Пересоздать БД
python init_db.py --force

# Проверить статистику
python init_db.py --stats
```

### Проблемы с загрузкой файлов
```bash
# Проверить права доступа
ls -la frontend/static/uploads/

# Создать директории
mkdir -p frontend/static/uploads/{original,medium,thumbnail}
chmod 755 frontend/static/uploads/*

# Проверить конфигурацию
python init_db.py --check-only
```

### Проблемы с OAuth
1. Проверьте правильность Client ID и Secret в `.env`
2. Убедитесь что redirect URIs настроены в консолях Google/Apple
3. Для локальной разработки используйте `http://localhost:5000`
4. Проверьте логи: `tail -f backend/logs/security.log`

### Проблемы с производительностью
```bash
# Анализ метрик
flask shell
>>> from app.utils.rate_limiter import get_rate_limit_stats
>>> print(get_rate_limit_stats())

# Очистка старых логов
python run.py cleanup-logs

# Проверка безопасности
python run.py security-check
```

## 🔒 Безопасность

### Рекомендации для разработки
- Используйте уникальный `SECRET_KEY`
- Не коммитьте `.env` файлы в репозиторий
- Регулярно обновляйте зависимости: `pip install -U -r requirements.txt`
- Проверяйте безопасность: `python run.py security-check`

### Рекомендации для продакшна
- **HTTPS обязательно**: `FORCE_HTTPS=true`
- **Сильные пароли**: Минимум 64 символа для `SECRET_KEY`
- **PostgreSQL**: Вместо SQLite для продакшна
- **Мониторинг**: Настройте алерты на основе логов безопасности
- **Backup**: Регулярные резервные копии БД и файлов
- **Firewall**: Ограничьте доступ к административным endpoints

## 📄 Лицензия

MIT License - см. файл LICENSE

## 🤝 Поддержка

### Самодиагностика
```bash
# Полная проверка системы
python init_db.py --check-only

# Проверка безопасности
python init_db.py --security-check

# Статистика и логи
python init_db.py --stats
tail -f backend/logs/app.log
```

### Получение помощи
1. 📖 Изучите документацию API
2. 🔍 Проверьте логи ошибок
3. 🛠 Запустите диагностические команды
4. 🐛 Создайте issue с подробным описанием проблемы

---

<div align="center">

**Collections** - Управляйте своими коллекциями профессионально! 🎯

[Документация API](docs/api_documentation.md) • [Примеры](docs/examples.md) • [Changelog](CHANGELOG.md)

</div>