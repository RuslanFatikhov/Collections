#!/usr/bin/env python3
"""
Упрощенная точка входа для запуска Flask приложения Collections
"""
import os
import sys
from dotenv import load_dotenv

# Добавляем путь к приложению в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Загружаем переменные окружения
load_dotenv()

def init_db(app):
    """Инициализация базы данных"""
    with app.app_context():
        try:
            # Импортируем все модели для создания таблиц
            from app.models.user import User
            from app.models.collection import Collection
            from app.models.item import Item
            
            print("🗄️ Создание таблиц базы данных...")
            from app import db
            db.create_all()
            print("✅ Таблицы созданы успешно!")
            
        except Exception as e:
            print(f"❌ Ошибка при создании базы данных: {str(e)}")
            sys.exit(1)

def setup_directories(app):
    """Создание необходимых директорий"""
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    
    # Создаем основную директорию для загрузок
    os.makedirs(upload_folder, exist_ok=True)
    
    # Создаем поддиректории
    subdirs = ['covers', 'items', 'avatars']
    sizes = ['original', 'medium', 'thumbnail']
    
    for subdir in subdirs:
        for size in sizes:
            dir_path = os.path.join(upload_folder, subdir, size)
            os.makedirs(dir_path, exist_ok=True)
    
    print(f"📁 Директории созданы: {upload_folder}")

if __name__ == '__main__':
    try:
        from app import create_app
        
        # Создаем приложение
        app = create_app()
        
        # Настройка директорий
        setup_directories(app)
        
        # Проверяем наличие базы данных при запуске
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///collections.db')
        if 'sqlite:///' in db_path:
            db_file = db_path.replace('sqlite:///', '')
            if not os.path.exists(db_file):
                print(f"🔧 База данных {db_file} не найдена. Создаем...")
                init_db(app)
        
        # Настройки для запуска
        host = os.environ.get('HOST', '127.0.0.1')
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('FLASK_ENV', 'development') == 'development'
        
        print("🚀 Запуск Collections...")
        print(f"🌐 URL: http://{host}:{port}")
        print(f"🔧 Режим: {'разработка' if debug else 'продакшн'}")
        print(f"🗄️ База данных: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        
        if app.config.get('MAIL_SUPPRESS_SEND'):
            print("📧 Email отключен (режим разработки)")
        else:
            print(f"📧 Email сервер: {app.config.get('MAIL_SERVER')}")
        
        if debug:
            print("\n" + "="*50)
            print("⚠️ ВНИМАНИЕ: Режим разработки!")
            print("Не используйте в продакшене!")
            print("="*50 + "\n")
        
        # Запуск приложения
        app.run(
            host=host,
            port=port,
            debug=debug
        )
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("\n📋 Возможные решения:")
        print("1. Установите недостающие зависимости:")
        print("   pip install Flask-Mail")
        print("2. Проверьте структуру проекта")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)