import time
import json
from functools import wraps
from collections import defaultdict, deque
from flask import request, jsonify, current_app
from flask_login import current_user
from datetime import datetime, timedelta

class RateLimiter:
    """Простой in-memory rate limiter"""
    
    def __init__(self):
        # Словарь для хранения запросов по IP/пользователю
        self.requests = defaultdict(deque)
        # Словарь для блокировки на определенное время
        self.blocked_until = defaultdict(float)
        
    def is_allowed(self, key, limit, window_seconds, block_seconds=None):
        """
        Проверка разрешен ли запрос
        
        Args:
            key (str): Ключ для идентификации (IP, user_id, etc.)
            limit (int): Максимальное количество запросов
            window_seconds (int): Временное окно в секундах
            block_seconds (int, optional): Время блокировки при превышении лимита
        
        Returns:
            tuple: (is_allowed: bool, remaining: int, reset_time: float)
        """
        now = time.time()
        
        # Проверяем, не заблокирован ли ключ
        if key in self.blocked_until and now < self.blocked_until[key]:
            return False, 0, self.blocked_until[key]
        
        # Удаляем старые записи из окна
        requests_deque = self.requests[key]
        while requests_deque and requests_deque[0] <= now - window_seconds:
            requests_deque.popleft()
        
        # Проверяем лимит
        if len(requests_deque) >= limit:
            # Превышен лимит
            if block_seconds:
                self.blocked_until[key] = now + block_seconds
                return False, 0, now + block_seconds
            else:
                # Время сброса - время самого старого запроса + окно
                reset_time = requests_deque[0] + window_seconds if requests_deque else now
                return False, 0, reset_time
        
        # Добавляем текущий запрос
        requests_deque.append(now)
        remaining = limit - len(requests_deque)
        reset_time = now + window_seconds
        
        return True, remaining, reset_time
    
    def cleanup_old_entries(self, max_age_hours=24):
        """Очистка старых записей для экономии памяти"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        # Очищаем старые запросы
        keys_to_remove = []
        for key, requests_deque in self.requests.items():
            while requests_deque and requests_deque[0] < cutoff_time:
                requests_deque.popleft()
            if not requests_deque:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.requests[key]
        
        # Очищаем истекшие блокировки
        now = time.time()
        expired_blocks = [key for key, until in self.blocked_until.items() if until <= now]
        for key in expired_blocks:
            del self.blocked_until[key]

# Глобальный экземпляр rate limiter
rate_limiter = RateLimiter()

def get_rate_limit_key():
    """Получение ключа для rate limiting (приоритет: user_id, затем IP)"""
    if current_user.is_authenticated:
        return f"user:{current_user.id}"
    
    # Получаем IP с учетом прокси
    ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
    if not ip:
        ip = request.headers.get('X-Real-IP', '')
    if not ip:
        ip = request.remote_addr
    
    return f"ip:{ip}"

def rate_limit(limit=100, window=3600, block_time=None, per_user=False):
    """
    Декоратор для rate limiting
    
    Args:
        limit (int): Максимальное количество запросов (по умолчанию 100)
        window (int): Временное окно в секундах (по умолчанию 1 час)
        block_time (int, optional): Время блокировки при превышении лимита
        per_user (bool): Использовать лимит на пользователя вместо IP
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Получаем ключ для rate limiting
            if per_user and current_user.is_authenticated:
                key = f"user:{current_user.id}"
            else:
                key = get_rate_limit_key()
            
            # Проверяем лимит
            allowed, remaining, reset_time = rate_limiter.is_allowed(
                key, limit, window, block_time
            )
            
            if not allowed:
                response_data = {
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Try again later.',
                    'retry_after': int(reset_time - time.time())
                }
                
                response = jsonify(response_data)
                response.status_code = 429
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(int(reset_time))
                response.headers['Retry-After'] = str(int(reset_time - time.time()))
                
                return response
            
            # Выполняем функцию
            result = func(*args, **kwargs)
            
            # Добавляем заголовки с информацией о лимитах
            if hasattr(result, 'headers'):
                result.headers['X-RateLimit-Limit'] = str(limit)
                result.headers['X-RateLimit-Remaining'] = str(remaining)
                result.headers['X-RateLimit-Reset'] = str(int(reset_time))
            
            return result
        
        return wrapper
    return decorator

# Предустановленные лимиты для разных типов операций
class RateLimits:
    """Предустановленные лимиты для разных операций"""
    
    # Аутентификация - строгие лимиты
    AUTH_LOGIN = {'limit': 5, 'window': 900, 'block_time': 1800}  # 5 попыток за 15 мин, блок на 30 мин
    AUTH_REGISTER = {'limit': 3, 'window': 3600, 'block_time': 3600}  # 3 регистрации в час
    
    # API операции - умеренные лимиты
    API_READ = {'limit': 1000, 'window': 3600}  # 1000 запросов на чтение в час
    API_WRITE = {'limit': 100, 'window': 3600}  # 100 запросов на запись в час
    API_DELETE = {'limit': 50, 'window': 3600}  # 50 удалений в час
    
    # Загрузка файлов - строгие лимиты
    FILE_UPLOAD = {'limit': 20, 'window': 3600}  # 20 загрузок в час
    
    # Просмотр публичных коллекций - мягкие лимиты
    PUBLIC_VIEW = {'limit': 2000, 'window': 3600}  # 2000 просмотров в час

def auth_rate_limit():
    """Rate limit для аутентификации"""
    return rate_limit(**RateLimits.AUTH_LOGIN)

def api_read_rate_limit():
    """Rate limit для чтения через API"""
    return rate_limit(**RateLimits.API_READ, per_user=True)

def api_write_rate_limit():
    """Rate limit для записи через API"""
    return rate_limit(**RateLimits.API_WRITE, per_user=True)

def api_delete_rate_limit():
    """Rate limit для удаления через API"""
    return rate_limit(**RateLimits.API_DELETE, per_user=True)

def file_upload_rate_limit():
    """Rate limit для загрузки файлов"""
    return rate_limit(**RateLimits.FILE_UPLOAD, per_user=True)

def public_view_rate_limit():
    """Rate limit для просмотра публичных страниц"""
    return rate_limit(**RateLimits.PUBLIC_VIEW)

# Функция для очистки старых данных (можно вызывать периодически)
def cleanup_rate_limiter():
    """Очистка старых данных rate limiter"""
    rate_limiter.cleanup_old_entries()

# Функция для получения статистики rate limiting
def get_rate_limit_stats():
    """Получение статистики по rate limiting"""
    now = time.time()
    stats = {
        'active_keys': len(rate_limiter.requests),
        'blocked_keys': len([k for k, v in rate_limiter.blocked_until.items() if v > now]),
        'total_requests': sum(len(deque) for deque in rate_limiter.requests.values())
    }
    return stats