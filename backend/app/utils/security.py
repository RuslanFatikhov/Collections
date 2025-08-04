# Заглушка для security модуля

class SecurityValidator:
    @staticmethod
    def validate_image_file(file):
        """Валидация файла изображения"""
        try:
            from app.utils.helpers import validate_image_content
            validate_image_content(file)
            return True, None
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def validate_collection_name(name):
        """Валидация названия коллекции"""
        if not name or not name.strip():
            return False, "Название коллекции не может быть пустым"
        
        if len(name.strip()) < 2:
            return False, "Название коллекции должно содержать минимум 2 символа"
        
        if len(name.strip()) > 100:
            return False, "Название коллекции не должно превышать 100 символов"
        
        return True, None
    
    @staticmethod
    def validate_custom_fields(fields):
        """Валидация пользовательских полей"""
        if not isinstance(fields, list):
            return False, "Поля должны быть списком"
        
        for field in fields:
            if not isinstance(field, dict):
                return False, "Каждое поле должно быть объектом"
            
            if 'name' not in field:
                return False, "У поля должно быть название"
        
        return True, None

def setup_security_middleware(app):
    """Заглушка для настройки middleware"""
    pass

def setup_upload_directory(path):
    """Заглушка для настройки директории загрузок"""
    import os
    os.makedirs(path, exist_ok=True)
    return True

def validate_json_input(required_fields=None, optional_fields=None):
    """Декоратор для валидации JSON входных данных"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Просто вызываем оригинальную функцию без валидации
            return func(*args, **kwargs)
        return wrapper
    return decorator

def sanitize_html(text):
    """Очистка HTML из текста"""
    import re
    if not text:
        return ""
    
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()
