from functools import wraps
from flask import jsonify, session, request, redirect, url_for
from flask_login import current_user
from app.models.admin import Admin

def admin_required(f):
    """
    Декоратор для проверки прав администратора для API endpoints
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Проверяем, авторизован ли пользователь
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Проверяем, является ли текущий пользователь администратором
        admin = Admin.query.filter_by(
            email=current_user.email,
            is_active=True
        ).first()
        
        if not admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def admin_page_required(f):
    """
    Декоратор для проверки прав администратора для HTML страниц
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Проверяем, авторизован ли пользователь
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # Проверяем, является ли текущий пользователь администратором
        admin = Admin.query.filter_by(
            email=current_user.email,
            is_active=True
        ).first()
        
        if not admin:
            return redirect(url_for('collections.index'))
        
        return f(*args, **kwargs)
    return decorated_function

def is_admin(user):
    """
    Проверить, является ли пользователь администратором
    """
    if not user or not user.is_authenticated:
        return False
    
    admin = Admin.query.filter_by(
        email=user.email,
        is_active=True
    ).first()
    
    return admin is not None

def get_current_admin():
    """
    Получить текущего администратора
    """
    if not current_user.is_authenticated:
        return None
    
    return Admin.query.filter_by(
        email=current_user.email,
        is_active=True
    ).first()