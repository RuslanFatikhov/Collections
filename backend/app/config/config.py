import os
from datetime import timedelta

class Config:
    # Базовые настройки Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Настройки базы данных
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///collections.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.environ.get('FLASK_ENV') == 'development'
    
    # Настройки сессий
    SESSION_COOKIE_SECURE = False  # True для HTTPS в продакшне
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    
    # Настройки загрузки файлов
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'frontend', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Настройки OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    APPLE_CLIENT_ID = os.environ.get('APPLE_CLIENT_ID')
    APPLE_CLIENT_SECRET = os.environ.get('APPLE_CLIENT_SECRET')
    APPLE_KEY_ID = os.environ.get('APPLE_KEY_ID')
    APPLE_TEAM_ID = os.environ.get('APPLE_TEAM_ID')
    APPLE_PRIVATE_KEY = os.environ.get('APPLE_PRIVATE_KEY')  # Путь к файлу или содержимое ключа
    
    # URL настройки
    BASE_URL = os.environ.get('BASE_URL') or 'http://localhost:5000'
    
    # Настройки логирования
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'app.log'
    
    @staticmethod
    def init_app(app):
        """Инициализация дополнительных настроек приложения"""
        # Создание директории для загрузок если не существует
        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        # Создание поддиректорий для разных типов файлов
        subdirs = ['covers', 'items', 'avatars']
        for subdir in subdirs:
            subdir_path = os.path.join(upload_folder, subdir)
            if not os.path.exists(subdir_path):
                os.makedirs(subdir_path)
        
        # Настройка логирования
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug and not app.testing:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            
            file_handler = RotatingFileHandler(
                'logs/collections.log', 
                maxBytes=10240000, 
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('Collections startup')


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    DEVELOPMENT = True
    
    # Более подробное логирование в разработке
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'
    
    # Менее строгие настройки безопасности для разработки
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False  # Отключаем CSRF для API в разработке
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Дополнительные настройки для разработки
        import logging
        app.logger.setLevel(logging.DEBUG)
        
        # Вывод всех SQL запросов в консоль
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


class TestingConfig(Config):
    """Конфигурация для тестирования"""
    TESTING = True
    DEBUG = True
    
    # Используем in-memory SQLite для тестов
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Отключаем CSRF для тестов
    WTF_CSRF_ENABLED = False
    
    # Отключаем логирование в файл для тестов
    LOG_FILE = None
    
    # Временная папка для загрузок в тестах
    UPLOAD_FOLDER = '/tmp/collections_test_uploads'


class ProductionConfig(Config):
    """Конфигурация для продакшна"""
    DEBUG = False
    TESTING = False
    
    # Строгие настройки безопасности
    SESSION_COOKIE_SECURE = True  # Только HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Настройки для PostgreSQL в продакшне
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://user:password@localhost/collections'
    
    # Настройки для внешнего хранилища файлов (например, S3)
    USE_S3 = os.environ.get('USE_S3', 'False').lower() == 'true'
    S3_BUCKET = os.environ.get('S3_BUCKET')
    S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY')
    S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY')
    S3_ENDPOINT = os.environ.get('S3_ENDPOINT')  # Для Timeweb Object Storage
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Настройки для продакшна
        import logging
        from logging.handlers import SysLogHandler
        
        # Логирование в syslog для продакшна
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)


# Словарь конфигураций
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Получить текущую конфигурацию на основе переменной окружения"""
    return config[os.environ.get('FLASK_ENV') or 'default']