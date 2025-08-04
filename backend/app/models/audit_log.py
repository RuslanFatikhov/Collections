# Заглушка для audit log модели

class AuditAction:
    LOGIN = 'login'
    LOGOUT = 'logout'
    LOGIN_FAILED = 'login_failed'
    USER_CREATE = 'user_create'
    USER_UPDATE = 'user_update'

class ResourceType:
    AUTH = 'auth'
    USER = 'user'
    SYSTEM = 'system'

class AuditLog:
    pass
