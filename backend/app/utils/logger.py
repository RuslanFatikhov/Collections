import json
import logging
from datetime import datetime
from flask import request, current_app
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError
from app.models.audit_log import AuditLog, db

# Настройка стандартного логгера Python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class AuditLogger:
    """Класс для логирования действий пользователей в базу данных"""
    
    @staticmethod
    def log_action(action, resource_type, resource_id=None, user_id=None, details=None):
        """
        Логирование действия пользователя
        
        Args:
            action (str): Тип действия (из AuditAction)
            resource_type (str): Тип ресурса (из ResourceType)
            resource_id (int, optional): ID ресурса
            user_id (int, optional): ID пользователя (если None, берется current_user)
            details (dict, optional): Дополнительная информация
        """
        try:
            # Получаем ID текущего пользователя если не передан
            if user_id is None and current_user.is_authenticated:
                user_id = current_user.id
            
            # Получаем информацию о запросе
            ip_address = None
            user_agent = None
            
            if request:
                ip_address = AuditLogger._get_client_ip()
                user_agent = request.headers.get('User-Agent', '')
            
            # Преобразуем details в JSON строку если это словарь
            details_json = None
            if details:
                if isinstance(details, dict):
                    details_json = json.dumps(details, ensure_ascii=False)
                else:
                    details_json = str(details)
            
            # Создаем запись в логе
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details_json
            )
            
            db.session.add(audit_log)
            db.session.commit()
            
            # Дублируем в стандартный лог
            logger.info(f"AUDIT: User {user_id} performed {action} on {resource_type} {resource_id}")
            
        except SQLAlchemyError as e:
            # Если не удалось записать в БД, логируем в файл
            logger.error(f"Failed to write audit log to database: {str(e)}")
            logger.info(f"AUDIT (FILE): User {user_id} performed {action} on {resource_type} {resource_id}")
            db.session.rollback()
        except Exception as e:
            logger.error(f"Unexpected error in audit logging: {str(e)}")
    
    @staticmethod
    def log_auth_attempt(success, user_id=None, email=None, provider=None):
        """Логирование попыток аутентификации"""
        from app.models.audit_log import AuditAction, ResourceType
        
        action = AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED
        details = {
            'success': success,
            'provider': provider or 'unknown'
        }
        
        if email:
            details['email'] = email
        
        AuditLogger.log_action(
            action=action,
            resource_type=ResourceType.AUTH,
            user_id=user_id,
            details=details
        )
    
    @staticmethod
    def log_collection_action(action, collection_id, collection_name=None, user_id=None):
        """Логирование действий с коллекциями"""
        from app.models.audit_log import ResourceType
        
        details = {}
        if collection_name:
            details['collection_name'] = collection_name
        
        AuditLogger.log_action(
            action=action,
            resource_type=ResourceType.COLLECTION,
            resource_id=collection_id,
            user_id=user_id,
            details=details
        )
    
    @staticmethod
    def log_item_action(action, item_id, collection_id=None, item_name=None, user_id=None):
        """Логирование действий с предметами"""
        from app.models.audit_log import ResourceType
        
        details = {}
        if collection_id:
            details['collection_id'] = collection_id
        if item_name:
            details['item_name'] = item_name
        
        AuditLogger.log_action(
            action=action,
            resource_type=ResourceType.ITEM,
            resource_id=item_id,
            user_id=user_id,
            details=details
        )
    
    @staticmethod
    def log_user_action(action, target_user_id, details=None, admin_user_id=None):
        """Логирование административных действий с пользователями"""
        from app.models.audit_log import ResourceType
        
        AuditLogger.log_action(
            action=action,
            resource_type=ResourceType.USER,
            resource_id=target_user_id,
            user_id=admin_user_id,
            details=details
        )
    
    @staticmethod
    def _get_client_ip():
        """Получение IP адреса клиента с учетом прокси"""
        if request.headers.get('X-Forwarded-For'):
            # Если запрос идет через прокси
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            # Nginx reverse proxy
            return request.headers.get('X-Real-IP')
        else:
            # Прямое подключение
            return request.remote_addr
    
    @staticmethod
    def get_user_activity(user_id, limit=50):
        """Получение последней активности пользователя"""
        try:
            logs = AuditLog.query.filter_by(user_id=user_id)\
                              .order_by(AuditLog.timestamp.desc())\
                              .limit(limit)\
                              .all()
            return [log.to_dict() for log in logs]
        except Exception as e:
            logger.error(f"Error getting user activity: {str(e)}")
            return []
    
    @staticmethod
    def get_resource_activity(resource_type, resource_id, limit=50):
        """Получение активности по конкретному ресурсу"""
        try:
            logs = AuditLog.query.filter_by(
                resource_type=resource_type,
                resource_id=resource_id
            ).order_by(AuditLog.timestamp.desc())\
             .limit(limit)\
             .all()
            return [log.to_dict() for log in logs]
        except Exception as e:
            logger.error(f"Error getting resource activity: {str(e)}")
            return []

# Декоратор для автоматического логирования
def log_action(action, resource_type, get_resource_id=None):
    """
    Декоратор для автоматического логирования действий
    
    Args:
        action (str): Тип действия
        resource_type (str): Тип ресурса
        get_resource_id (callable, optional): Функция для получения resource_id из результата
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                # Получаем resource_id из результата если указана функция
                resource_id = None
                if get_resource_id and callable(get_resource_id):
                    resource_id = get_resource_id(result)
                
                # Логируем действие
                AuditLogger.log_action(
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id
                )
                
                return result
            except Exception as e:
                logger.error(f"Error in logged function {func.__name__}: {str(e)}")
                raise
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator