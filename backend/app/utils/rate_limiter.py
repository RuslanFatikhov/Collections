# Заглушка для rate limiter

def auth_rate_limit():
    """Декоратор для rate limiting"""
    def decorator(func):
        return func
    return decorator

def cleanup_rate_limiter():
    """Очистка rate limiter"""
    pass

def api_read_rate_limit():
    """Декоратор для rate limiting API чтения"""
    def decorator(func):
        return func
    return decorator

def api_write_rate_limit():
    """Декоратор для rate limiting API записи"""
    def decorator(func):
        return func
    return decorator

def get_rate_limit_stats():
    """Получение статистики rate limiting"""
    return {}

def api_delete_rate_limit():
    """Декоратор для rate limiting API удаления"""
    def decorator(func):
        return func
    return decorator

def rate_limit():
    """Декоратор для общего rate limiting"""
    def decorator(func):
        return func
    return decorator

def file_upload_rate_limit():
    """Декоратор для rate limiting загрузки файлов"""
    def decorator(func):
        return func
    return decorator

def public_view_rate_limit():
    """Декоратор для rate limiting публичного просмотра"""
    def decorator(func):
        return func
    return decorator
