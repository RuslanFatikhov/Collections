import re
import os
import hashlib
from functools import wraps
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
from PIL import Image
import magic

class SecurityValidator:
    """Класс для валидации входных данных"""
    
    # Регулярные выражения для валидации
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]{3,30}$')
    COLLECTION_NAME_REGEX = re.compile(r'^[a-zA-Z0-9\s\-_\.]{1,100}$')
    
    # Разрешенные типы файлов для изображений
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ALLOWED_IMAGE_MIMES = {
        'image/png', 'image/jpeg', 'image/gif', 'image/webp'
    }
    
    # Максимальные размеры
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_IMAGE_DIMENSIONS = (4000, 4000)  # 4000x4000 пикселей
    MAX_TEXT_LENGTH = 10000
    MAX_DESCRIPTION_LENGTH = 5000
    MAX_COLLECTION_FIELDS = 20
    
    @classmethod
    def validate_email(cls, email):
        """Валидация email адреса"""
        if not email or not isinstance(email, str):
            return False, "Email is required"
        
        if len(email) > 254:
            return False, "Email is too long"
        
        if not cls.EMAIL_REGEX.match(email):
            return False, "Invalid email format"
        
        return True, "Valid"
    
    @classmethod
    def validate_text(cls, text, min_length=1, max_length=None, field_name="Text"):
        """Валидация текстовых полей"""
        if not isinstance(text, str):
            return False, f"{field_name} must be a string"
        
        text = text.strip()
        
        if len(text) < min_length:
            return False, f"{field_name} must be at least {min_length} characters long"
        
        max_len = max_length or cls.MAX_TEXT_LENGTH
        if len(text) > max_len:
            return False, f"{field_name} must be no more than {max_len} characters long"
        
        # Проверка на потенциально опасные символы
        if cls._contains_dangerous_chars(text):
            return False, f"{field_name} contains invalid characters"
        
        return True, "Valid"
    
    @classmethod
    def validate_collection_name(cls, name):
        """Валидация названия коллекции"""
        if not name or not isinstance(name, str):
            return False, "Collection name is required"
        
        name = name.strip()
        
        if not name:
            return False, "Collection name cannot be empty"
        
        if len(name) > 100:
            return False, "Collection name is too long"
        
        if not cls.COLLECTION_NAME_REGEX.match(name):
            return False, "Collection name contains invalid characters"
        
        return True, "Valid"
    
    @classmethod
    def validate_custom_fields(cls, fields):
        """Валидация кастомных полей коллекции"""
        if not isinstance(fields, list):
            return False, "Fields must be a list"
        
        if len(fields) > cls.MAX_COLLECTION_FIELDS:
            return False, f"Too many fields (max {cls.MAX_COLLECTION_FIELDS})"
        
        field_names = set()
        for field in fields:
            if not isinstance(field, dict):
                return False, "Each field must be an object"
            
            # Проверяем обязательные поля
            if 'name' not in field or 'type' not in field:
                return False, "Each field must have 'name' and 'type'"
            
            # Валидируем имя поля
            field_name = field['name']
            is_valid, message = cls.validate_text(field_name, 1, 50, "Field name")
            if not is_valid:
                return False, message
            
            # Проверяем уникальность имен полей
            if field_name.lower() in field_names:
                return False, f"Duplicate field name: {field_name}"
            field_names.add(field_name.lower())
            
            # Валидируем тип поля
            allowed_types = ['text', 'number', 'date', 'checkbox', 'image']
            if field['type'] not in allowed_types:
                return False, f"Invalid field type: {field['type']}"
        
        return True, "Valid"
    
    @classmethod
    def validate_image_file(cls, file):
        """Валидация загружаемого изображения"""
        if not file:
            return False, "No file provided"
        
        if not file.filename:
            return False, "No filename provided"
        
        # Проверяем расширение файла
        filename = secure_filename(file.filename)
        if '.' not in filename:
            return False, "File has no extension"
        
        ext = filename.rsplit('.', 1)[1].lower()
        if ext not in cls.ALLOWED_IMAGE_EXTENSIONS:
            return False, f"Invalid file extension. Allowed: {', '.join(cls.ALLOWED_IMAGE_EXTENSIONS)}"
        
        # Проверяем размер файла
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > cls.MAX_IMAGE_SIZE:
            return False, f"File too large. Max size: {cls.MAX_IMAGE_SIZE // (1024*1024)}MB"
        
        # Проверяем MIME-тип
        try:
            file_content = file.read(1024)  # Читаем первые 1024 байта
            file.seek(0)
            
            mime_type = magic.from_buffer(file_content, mime=True)
            if mime_type not in cls.ALLOWED_IMAGE_MIMES:
                return False, f"Invalid file type: {mime_type}"
        except Exception:
            # Если magic недоступен, пропускаем проверку MIME
            pass
        
        # Проверяем, что это действительно изображение
        try:
            with Image.open(file) as img:
                # Проверяем размеры изображения
                if img.size[0] > cls.MAX_IMAGE_DIMENSIONS[0] or img.size[1] > cls.MAX_IMAGE_DIMENSIONS[1]:
                    return False, f"Image too large. Max dimensions: {cls.MAX_IMAGE_DIMENSIONS[0]}x{cls.MAX_IMAGE_DIMENSIONS[1]}"
                
                # Проверяем, что изображение не повреждено
                img.verify()
            
            file.seek(0)  # Возвращаем указатель в начало
            return True, "Valid"
            
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"
    
    @classmethod
    def _contains_dangerous_chars(cls, text):
        """Проверка на потенциально опасные символы"""
        # Проверяем на SQL injection паттерны
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS скрипты
            r'javascript:',  # JavaScript протокол
            r'on\w+\s*=',  # HTML события (onclick, onload, etc.)
            r'<iframe[^>]*>',  # Встроенные фреймы
            r'<object[^>]*>',  # Объекты
            r'<embed[^>]*>',  # Встроенный контент
        ]
        
        text_lower = text.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                return True
        
        return False
    
    @classmethod
    def sanitize_filename(cls, filename):
        """Безопасное имя файла"""
        if not filename:
            return "unnamed_file"
        
        # Используем werkzeug для базовой очистки
        safe_name = secure_filename(filename)
        
        # Дополнительная очистка
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', safe_name)
        
        # Ограничиваем длину
        if len(safe_name) > 255:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[:255-len(ext)] + ext
        
        return safe_name or "unnamed_file"
    
    @classmethod
    def generate_safe_filename(cls, original_filename, user_id=None):
        """Генерация безопасного уникального имени файла"""
        if not original_filename:
            return "unnamed_file"
        
        # Получаем расширение
        _, ext = os.path.splitext(original_filename)
        ext = ext.lower()
        
        # Генерируем уникальное имя на основе времени и содержимого
        import time
        timestamp = str(int(time.time() * 1000000))  # Микросекунды
        
        # Добавляем user_id для уникальности между пользователями
        if user_id:
            unique_part = f"{user_id}_{timestamp}"
        else:
            unique_part = timestamp
        
        # Создаем хеш для дополнительной уникальности
        hash_input = f"{original_filename}{unique_part}".encode('utf-8')
        file_hash = hashlib.md5(hash_input).hexdigest()[:8]
        
        return f"{unique_part}_{file_hash}{ext}"

class SecurityHeaders:
    """Класс для настройки security headers"""
    
    @staticmethod
    def apply_security_headers(response):
        """Применение security headers к ответу"""
        
        # Content Security Policy
        csp = "default-src 'self'; " \
              "script-src 'self' 'unsafe-inline' https://apis.google.com https://accounts.google.com; " \
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; " \
              "font-src 'self' https://fonts.gstatic.com; " \
              "img-src 'self' data: https:; " \
              "connect-src 'self' https://accounts.google.com; " \
              "frame-src https://accounts.google.com; " \
              "object-src 'none'; " \
              "base-uri 'self'"
        
        response.headers['Content-Security-Policy'] = csp
        
        # Другие security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # HSTS (только для HTTPS)
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    @staticmethod
    def force_https():
        """Принудительное перенаправление на HTTPS"""
        if not request.is_secure and not current_app.debug:
            # Проверяем заголовки от прокси (например, от nginx)
            if request.headers.get('X-Forwarded-Proto', 'http') != 'https':
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)
        return None

def validate_json_input(required_fields=None, optional_fields=None):
    """
    Декоратор для валидации JSON входных данных
    
    Args:
        required_fields (dict): Словарь обязательных полей {field_name: validator_function}
        optional_fields (dict): Словарь опциональных полей {field_name: validator_function}
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Проверяем, что запрос содержит JSON
            if not request.is_json:
                return jsonify({'error': 'Request must contain JSON data'}), 400
            
            try:
                data = request.get_json()
            except Exception:
                return jsonify({'error': 'Invalid JSON format'}), 400
            
            if not isinstance(data, dict):
                return jsonify({'error': 'JSON data must be an object'}), 400
            
            # Проверяем обязательные поля
            if required_fields:
                for field_name, validator in required_fields.items():
                    if field_name not in data:
                        return jsonify({'error': f'Missing required field: {field_name}'}), 400
                    
                    if validator:
                        is_valid, message = validator(data[field_name])
                        if not is_valid:
                            return jsonify({'error': f'Invalid {field_name}: {message}'}), 400
            
            # Проверяем опциональные поля
            if optional_fields:
                for field_name, validator in optional_fields.items():
                    if field_name in data and validator:
                        is_valid, message = validator(data[field_name])
                        if not is_valid:
                            return jsonify({'error': f'Invalid {field_name}: {message}'}), 400
            
            # Проверяем на неожиданные поля
            allowed_fields = set()
            if required_fields:
                allowed_fields.update(required_fields.keys())
            if optional_fields:
                allowed_fields.update(optional_fields.keys())
            
            unexpected_fields = set(data.keys()) - allowed_fields
            if unexpected_fields:
                return jsonify({
                    'error': f'Unexpected fields: {", ".join(unexpected_fields)}'
                }), 400
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_admin():
    """Декоратор для проверки прав администратора"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            
            if not getattr(current_user, 'is_admin', False):
                return jsonify({'error': 'Admin privileges required'}), 403
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def sanitize_html(text):
    """Базовая очистка HTML из текста"""
    if not text:
        return text
    
    # Удаляем HTML теги
    clean_text = re.sub(r'<[^>]+>', '', text)
    
    # Декодируем HTML entities
    import html
    clean_text = html.unescape(clean_text)
    
    return clean_text.strip()

def check_file_safety(file_path):
    """Проверка безопасности загруженного файла"""
    try:
        # Проверяем, что файл существует
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        # Проверяем размер файла
        file_size = os.path.getsize(file_path)
        if file_size > SecurityValidator.MAX_IMAGE_SIZE:
            return False, "File too large"
        
        # Проверяем, что это изображение
        try:
            with Image.open(file_path) as img:
                # Проверяем размеры
                if img.size[0] > SecurityValidator.MAX_IMAGE_DIMENSIONS[0] or \
                   img.size[1] > SecurityValidator.MAX_IMAGE_DIMENSIONS[1]:
                    return False, "Image dimensions too large"
                
                # Проверяем формат
                if img.format.lower() not in ['png', 'jpeg', 'gif', 'webp']:
                    return False, "Unsupported image format"
                
                # Проверяем целостность
                img.verify()
                
            return True, "Safe"
            
        except Exception as e:
            return False, f"Invalid image: {str(e)}"
    
    except Exception as e:
        return False, f"Error checking file: {str(e)}"

# Middleware для автоматического применения security headers
def setup_security_middleware(app):
    """Настройка middleware для безопасности"""
    
    @app.before_request
    def security_before_request():
        # Принудительное HTTPS в продакшене
        redirect_response = SecurityHeaders.force_https()
        if redirect_response:
            return redirect_response
    
    @app.after_request
    def security_after_request(response):
        # Применяем security headers ко всем ответам
        return SecurityHeaders.apply_security_headers(response)
    
    return app

# Функция для создания папки uploads с правильными правами
def setup_upload_directory(upload_path):
    """Создание и настройка папки для загрузок"""
    try:
        os.makedirs(upload_path, exist_ok=True)
        
        # Устанавливаем безопасные права доступа (только для владельца)
        os.chmod(upload_path, 0o755)
        
        # Создаем .htaccess для дополнительной защиты (если используется Apache)
        htaccess_path = os.path.join(upload_path, '.htaccess')
        if not os.path.exists(htaccess_path):
            with open(htaccess_path, 'w') as f:
                f.write("""
# Запрещаем выполнение PHP и других скриптов
php_flag engine off
AddType text/plain .php .php3 .phtml .pht .pl .py .jsp .asp .sh .cgi

# Запрещаем доступ к потенциально опасным файлам
<Files ~ "\.(htaccess|htpasswd|ini|log|sh|inc|bak)$">
    Order Allow,Deny
    Deny from all
</Files>

# Разрешаем только изображения
<FilesMatch "\.(jpg|jpeg|png|gif|webp)$">
    Order Allow,Deny
    Allow from all
</FilesMatch>
""")
        
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to setup upload directory: {str(e)}")
        return False