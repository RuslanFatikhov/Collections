#!/usr/bin/env python3
"""
Точка входа для запуска Flask приложения Collections
"""
import os
import sys
import logging
import signal
import atexit
from dotenv import load_dotenv

# Добавляем путь к приложению в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Загружаем переменные окружения
load_dotenv()

from app import create_app, db
from app.utils.security import setup_security_middleware, setup_upload_directory
from app.utils.rate_limiter import cleanup_rate_limiter
from app.utils.logger import AuditLogger
from app.models.audit_log import AuditAction, ResourceType

# Создание приложения
app = create_app()

# Настройка системы безопасности
setup_security_middleware(app)

def setup_logging():
    """Настройка логирования"""
    # Создаем директорию для логов
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Настройка основного логгера
    logging.basicConfig(
        level=logging.INFO if not app.debug else logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'app.log')),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Настройка логгера для загрузок
    upload_logger = logging.getLogger('uploads')
    upload_handler = logging.FileHandler(os.path.join(log_dir, 'uploads.log'))
    upload_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    upload_logger.addHandler(upload_handler)
    upload_logger.setLevel(logging.INFO)
    
    # Настройка логгера для безопасности
    security_logger = logging.getLogger('security')
    security_handler = logging.FileHandler(os.path.join(log_dir, 'security.log'))
    security_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.WARNING)
    
    # Ограничиваем логирование внешних библиотек
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def setup_directories():
    """Создание и настройка необходимых директорий"""
    # Создаем директорию для загрузок
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    if not setup_upload_directory(upload_folder):
        app.logger.error(f"Failed to setup upload directory: {upload_folder}")
        sys.exit(1)
    
    # Создаем поддиректории для разных размеров изображений
    for size in ['original', 'medium', 'thumbnail']:
        size_dir = os.path.join(upload_folder, size)
        os.makedirs(size_dir, exist_ok=True)
        os.chmod(size_dir, 0o755)
    
    app.logger.info(f"Upload directories setup completed: {upload_folder}")

def init_db():
    """Инициализация базы данных"""
    with app.app_context():
        try:
            # Импортируем все модели для создания таблиц
            from app.models.user import User
            from app.models.collection import Collection
            from app.models.item import Item
            from app.models.audit_log import AuditLog
            
            print("Создание таблиц базы данных...")
            db.create_all()
            print("Таблицы созданы успешно!")
            
            # Логируем инициализацию базы данных
            AuditLogger.log_action(
                action='DATABASE_INIT',
                resource_type=ResourceType.SYSTEM,
                details={'action': 'database_initialized'}
            )
            
        except Exception as e:
            print(f"Ошибка при создании базы данных: {str(e)}")
            app.logger.error(f"Database initialization failed: {str(e)}")
            sys.exit(1)

def cleanup_on_exit():
    """Очистка ресурсов при завершении приложения"""
    try:
        # Очищаем данные rate limiter
        cleanup_rate_limiter()
        
        # Логируем завершение работы приложения
        with app.app_context():
            AuditLogger.log_action(
                action='APPLICATION_SHUTDOWN',
                resource_type=ResourceType.SYSTEM,
                details={'action': 'application_shutdown'}
            )
        
        app.logger.info("Application shutdown completed")
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    print(f"\nReceived signal {signum}. Shutting down gracefully...")
    cleanup_on_exit()
    sys.exit(0)

@app.cli.command()
def create_db():
    """CLI команда для создания базы данных"""
    init_db()

@app.cli.command()
def drop_db():
    """CLI команда для удаления базы данных"""
    with app.app_context():
        print("Удаление таблиц базы данных...")
        db.drop_all()
        print("Таблицы удалены!")

@app.cli.command()
def reset_db():
    """CLI команда для пересоздания базы данных"""
    with app.app_context():
        print("Пересоздание базы данных...")
        db.drop_all()
        db.create_all()
        print("База данных пересоздана!")

@app.cli.command()
def create_admin():
    """CLI команда для создания администратора"""
    email = input("Введите email администратора: ")
    name = input("Введите имя администратора: ")
    
    with app.app_context():
        from app.models.user import User
        
        # Проверяем, существует ли пользователь
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_admin = True
            user.name = name
            print(f"Пользователь {email} назначен администратором")
        else:
            # Создаем нового пользователя-администратора
            user = User(email=email, name=name, is_admin=True)
            db.session.add(user)
            print(f"Создан новый администратор: {email}")
        
        db.session.commit()
        
        # Логируем создание администратора
        AuditLogger.log_action(
            action=AuditAction.USER_CREATE,
            resource_type=ResourceType.USER,
            resource_id=user.id,
            details={'action': 'admin_created', 'email': email}
        )

@app.cli.command()
def cleanup_logs():
    """CLI команда для очистки старых логов"""
    import glob
    from datetime import datetime, timedelta
    
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    cutoff_date = datetime.now() - timedelta(days=30)  # Удаляем логи старше 30 дней
    
    # Находим старые лог файлы (если они ротируются с датой)
    old_files = []
    for pattern in ['*.log.*', '*.log.old']:
        old_files.extend(glob.glob(os.path.join(log_dir, pattern)))
    
    deleted_count = 0
    for file_path in old_files:
        try:
            file_date = datetime.fromtimestamp(os.path.getctime(file_path))
            if file_date < cutoff_date:
                os.remove(file_path)
                deleted_count += 1
                print(f"Deleted old log file: {file_path}")
        except Exception as e:
            print(f"Error deleting {file_path}: {str(e)}")
    
    print(f"Cleanup completed. Deleted {deleted_count} old log files.")

@app.cli.command()
def security_check():
    """CLI команда для проверки безопасности"""
    print("Выполнение проверки безопасности...")
    
    issues = []
    
    # Проверяем конфигурацию
    if app.config.get('SECRET_KEY') == 'dev-key-change-in-production':
        issues.append("WARNING: Using default SECRET_KEY in production")
    
    if app.debug and os.environ.get('FLASK_ENV') == 'production':
        issues.append("WARNING: Debug mode enabled in production")
    
    # Проверяем директории
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    if not os.path.exists(upload_folder):
        issues.append(f"WARNING: Upload folder does not exist: {upload_folder}")
    
    # Проверяем права доступа
    if os.path.exists(upload_folder):
        stat_info = os.stat(upload_folder)
        if stat_info.st_mode & 0o077:  # Проверяем права для группы и других
            issues.append(f"WARNING: Upload folder has loose permissions: {upload_folder}")
    
    # Проверяем наличие HTTPS в продакшене
    if (os.environ.get('FLASK_ENV') == 'production' and 
        not os.environ.get('FORCE_HTTPS', '').lower() == 'true'):
        issues.append("WARNING: HTTPS not enforced in production")
    
    if issues:
        print("Security issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    else:
        print("No security issues found.")
        return 0

@app.shell_context_processor
def make_shell_context():
    """Контекст для Flask shell"""
    from app.models.user import User
    from app.models.collection import Collection
    from app.models.item import Item
    from app.models.audit_log import AuditLog, AuditAction, ResourceType
    from app.utils.logger import AuditLogger
    from app.utils.rate_limiter import get_rate_limit_stats
    
    return {
        'db': db,
        'User': User,
        'Collection': Collection,
        'Item': Item,
        'AuditLog': AuditLog,
        'AuditAction': AuditAction,
        'ResourceType': ResourceType,
        'AuditLogger': AuditLogger,
        'get_rate_limit_stats': get_rate_limit_stats
    }

if __name__ == '__main__':
    # Настройка обработчиков сигналов для graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(cleanup_on_exit)
    
    # Настройка логирования
    setup_logging()
    
    # Настройка директорий
    setup_directories()
    
    # Проверяем наличие базы данных при запуске
    db_path = app.config.get('DATABASE_URL', 'sqlite:///collections.db')
    if 'sqlite:///' in db_path:
        db_file = db_path.replace('sqlite:///', '')
        if not os.path.exists(db_file):
            print(f"База данных {db_file} не найдена. Создаем...")
            init_db()
    
    # Логируем запуск приложения
    with app.app_context():
        try:
            AuditLogger.log_action(
                action='APPLICATION_START',
                resource_type=ResourceType.SYSTEM,
                details={
                    'action': 'application_start',
                    'debug_mode': app.debug,
                    'environment': os.environ.get('FLASK_ENV', 'development')
                }
            )
        except Exception as e:
            app.logger.warning(f"Could not log application start: {str(e)}")
    
    # Настройки для запуска
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    # Проверяем безопасность в продакшене
    if not debug:
        print("Running security check...")
        security_exit_code = None
        with app.app_context():
            import subprocess
            result = subprocess.run([sys.executable, __file__, 'security-check'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print("Security issues detected. Please review before deployment.")
                print(result.stdout)
    
    print(f"Запуск Collections на http://{host}:{port}")
    print(f"Режим отладки: {'включен' if debug else 'отключен'}")
    print(f"Окружение: {os.environ.get('FLASK_ENV', 'development')}")
    
    if debug:
        print("\n" + "="*50)
        print("ВНИМАНИЕ: Приложение запущено в режиме разработки!")
        print("Не используйте этот режим в продакшене!")
        print("="*50 + "\n")
    
    # Запуск приложения
    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True,
            use_reloader=debug  # Автоперезагрузка только в debug режиме
        )
    except KeyboardInterrupt:
        print("\nПриложение остановлено пользователем")
    except Exception as e:
        app.logger.error(f"Failed to start application: {str(e)}")
        print(f"Ошибка запуска приложения: {str(e)}")
        sys.exit(1)