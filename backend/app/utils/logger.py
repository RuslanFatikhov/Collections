# Заглушка для audit logger

class AuditLogger:
    @staticmethod
    def log_action(action, resource_type, **kwargs):
        """Логирование действий"""
        pass
    
    @staticmethod
    def log_auth_attempt(success, user_id=None, email=None, provider=None):
        """Логирование попыток авторизации"""
        pass
