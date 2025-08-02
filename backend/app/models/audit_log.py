from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Может быть null для анонимных действий
    action = Column(String(100), nullable=False)  # Тип действия: CREATE, UPDATE, DELETE, VIEW, LOGIN, etc.
    resource_type = Column(String(50), nullable=False)  # Тип ресурса: USER, COLLECTION, ITEM, etc.
    resource_id = Column(Integer, nullable=True)  # ID ресурса (может быть null для общих действий)
    ip_address = Column(String(45), nullable=True)  # IPv4 или IPv6
    user_agent = Column(Text, nullable=True)  # User Agent браузера
    details = Column(Text, nullable=True)  # Дополнительная информация в JSON формате
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Связь с пользователем
    user = relationship("User", backref="audit_logs")
    
    def __init__(self, user_id=None, action=None, resource_type=None, resource_id=None, 
                 ip_address=None, user_agent=None, details=None):
        self.user_id = user_id
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.details = details
    
    def __repr__(self):
        return f'<AuditLog {self.id}: {self.action} {self.resource_type}>'
    
    def to_dict(self):
        """Преобразование в словарь для JSON ответов"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'details': self.details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

# Константы для типов действий
class AuditAction:
    # Аутентификация
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'
    LOGIN_FAILED = 'LOGIN_FAILED'
    
    # Пользователи
    USER_CREATE = 'USER_CREATE'
    USER_UPDATE = 'USER_UPDATE'
    USER_DELETE = 'USER_DELETE'
    USER_VIEW = 'USER_VIEW'
    
    # Коллекции
    COLLECTION_CREATE = 'COLLECTION_CREATE'
    COLLECTION_UPDATE = 'COLLECTION_UPDATE'
    COLLECTION_DELETE = 'COLLECTION_DELETE'
    COLLECTION_VIEW = 'COLLECTION_VIEW'
    COLLECTION_SHARE = 'COLLECTION_SHARE'
    
    # Предметы
    ITEM_CREATE = 'ITEM_CREATE'
    ITEM_UPDATE = 'ITEM_UPDATE'
    ITEM_DELETE = 'ITEM_DELETE'
    ITEM_VIEW = 'ITEM_VIEW'
    
    # Администрирование
    ADMIN_ACCESS = 'ADMIN_ACCESS'
    USER_BLOCK = 'USER_BLOCK'
    USER_UNBLOCK = 'USER_UNBLOCK'
    COLLECTION_BLOCK = 'COLLECTION_BLOCK'
    COLLECTION_UNBLOCK = 'COLLECTION_UNBLOCK'

# Константы для типов ресурсов
class ResourceType:
    USER = 'USER'
    COLLECTION = 'COLLECTION'
    ITEM = 'ITEM'
    SYSTEM = 'SYSTEM'
    AUTH = 'AUTH'