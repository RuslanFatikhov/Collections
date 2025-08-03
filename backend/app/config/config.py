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
    
    # Настройки Email
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')
    MAIL_MAX_EMAILS = os.environ.get('MAIL_MAX_EMAILS') or 100
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'false').lower() in ['true', 'on', '1']
    
    # URL настройки
    BASE_URL = os.environ.get('BASE_URL') or 'http://localhost:5000'
    
    # Настройки безопасности
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 час
    
    # Настройки rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'
    RATELIMIT_DEFAULT = "100 per hour"
    
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
            
            # Создание поддиректорий для разных размеров
            for size in ['original', 'medium', 'thumbnail']:
                size_path = os.path.join(subdir_path, size)
                if not os.path.exists(size_path):
                    os.makedirs(size_path)
        
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
    
    # Отключаем отправку email в разработке
    MAIL_SUPPRESS_SEND = True
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Дополнительные настройки для разработки
        import logging
        app.logger.setLevel(logging.DEBUG)
        
        # Вывод всех SQL запросов в консоль
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        
        # Логируем email в консоль вместо отправки
        if app.config['MAIL_SUPPRESS_SEND']:
            print("=== EMAIL SUPPRESSED IN DEVELOPMENT ===")


class TestingConfig(Config):
    """Конфигурация для тестирования"""
    TESTING = True
    DEBUG = True
    
    # Используем in-memory SQLite для тестов
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Отключаем CSRF для тестов
    WTF_CSRF_ENABLED = False
    
    # Отключаем отправку email в тестах
    MAIL_SUPPRESS_SEND = True
    
    # Отключаем логирование в файл для тестов
    LOG_FILE = None
    
    # Временная папка для загрузок в тестах
    UPLOAD_FOLDER = '/tmp/collections_test_uploads'
    
    # Быстрые rate limits для тестов
    RATELIMIT_DEFAULT = "1000 per hour"


class ProductionConfig(Config):
    """Конфигурация для продакшна"""
    DEBUG = False
    TESTING = False
    
    # Строгие настройки безопасности
    SESSION_COOKIE_SECURE = True  # Только HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Включаем CSRF защиту
    WTF_CSRF_ENABLED = True
    
    # Настройки для PostgreSQL в продакшне
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://user:password@localhost/collections'
    
    # Настройки для внешнего хранилища файлов (например, S3)
    USE_S3 = os.environ.get('USE_S3', 'False').lower() == 'true'
    S3_BUCKET = os.environ.get('S3_BUCKET')
    S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY')
    S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY')
    S3_ENDPOINT = os.environ.get('S3_ENDPOINT')  # Для Timeweb Object Storage
    
    # Включаем отправку email в продакшне
    MAIL_SUPPRESS_SEND = False
    
    # Строгие rate limits для продакшна
    RATELIMIT_DEFAULT = "60 per hour"
    
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
        
        # Проверяем обязательные настройки для продакшна
        required_settings = ['SECRET_KEY', 'MAIL_SERVER', 'MAIL_USERNAME', 'MAIL_PASSWORD']
        missing_settings = [setting for setting in required_settings 
                          if not app.config.get(setting)]
        
        if missing_settings:
            raise ValueError(f"Missing required production settings: {', '.join(missing_settings)}")


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