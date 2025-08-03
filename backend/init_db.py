#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных Collections
Использование: python init_db.py [--force] [--sample-data] [--admin]
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User
from app.models.collection import Collection
from app.models.item import Item
from app.models.audit_log import AuditLog, AuditAction, ResourceType
from app.utils.logger import AuditLogger
from app.utils.security import setup_upload_directory


def init_database(force=False, sample_data=False, create_admin_user=False):
    """Инициализация базы данных"""
    
    app = create_app()
    
    with app.app_context():
        # Проверяем существует ли база данных
        db_exists = False
        try:
            # Пытаемся выполнить простой запрос
            result = db.session.execute(db.text('SELECT 1'))
            db_exists = True
        except Exception:
            db_exists = False
        
        if db_exists and not force:
            print("База данных уже существует!")
            print("Используйте --force для пересоздания")
            return False
        
        if force and db_exists:
            print("Удаляем существующие таблицы...")
            db.drop_all()
        
        print("Создаем таблицы базы данных...")
        db.create_all()
        
        print("Таблицы созданы успешно:")
        print("- users")
        print("- collections") 
        print("- items")
        print("- audit_logs")
        
        # Логируем инициализацию БД
        try:
            AuditLogger.log_action(
                action=AuditAction.SYSTEM,
                resource_type=ResourceType.SYSTEM,
                details={
                    'action': 'database_initialized',
                    'force': force,
                    'sample_data': sample_data
                }
            )
        except Exception as e:
            print(f"Предупреждение: Не удалось создать аудит-лог: {e}")
        
        if create_admin_user:
            create_admin()
        
        if sample_data:
            create_sample_data()
        
        print("\nБаза данных инициализирована успешно!")
        return True


def create_admin():
    """Создание администратора"""
    print("\n=== Создание администратора ===")
    
    email = input("Введите email администратора: ").strip()
    if not email:
        print("Email не может быть пустым!")
        return False
    
    name = input("Введите имя администратора: ").strip()
    if not name:
        print("Имя не может быть пустым!")
        return False
    
    # Проверяем, существует ли пользователь
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        existing_user.is_admin = True
        existing_user.name = name
        existing_user.is_active = True
        db.session.commit()
        
        print(f"✓ Пользователь {email} назначен администратором")
        
        # Логируем обновление администратора
        AuditLogger.log_action(
            action=AuditAction.USER_UPDATE,
            resource_type=ResourceType.USER,
            resource_id=existing_user.id,
            user_id=existing_user.id,
            details={
                'action': 'admin_role_granted',
                'email': email
            }
        )
    else:
        # Создаем нового пользователя-администратора
        admin_user = User(
            email=email,
            name=name,
            is_admin=True,
            is_active=True,
            google_id=f"admin_{email}_{int(datetime.now().timestamp())}"  # Временный ID
        )
        db.session.add(admin_user)
        db.session.commit()
        
        print(f"✓ Создан новый администратор: {email}")
        
        # Логируем создание администратора
        AuditLogger.log_action(
            action=AuditAction.USER_CREATE,
            resource_type=ResourceType.USER,
            resource_id=admin_user.id,
            user_id=admin_user.id,
            details={
                'action': 'admin_created',
                'email': email
            }
        )
    
    print("Администратор создан успешно!")
    return True


def create_sample_data():
    """Создание тестовых данных"""
    print("\n=== Создание тестовых данных ===")
    
    # Создаем тестового пользователя
    test_user = User(
        email='test@example.com',
        name='Тестовый пользователь',
        google_id='test_google_id_12345',
        avatar_url='https://via.placeholder.com/150',
        is_active=True
    )
    db.session.add(test_user)
    db.session.commit()
    
    print(f"✓ Создан тестовый пользователь: {test_user.email}")
    
    # Логируем создание тестового пользователя
    AuditLogger.log_action(
        action=AuditAction.USER_CREATE,
        resource_type=ResourceType.USER,
        resource_id=test_user.id,
        user_id=test_user.id,
        details={
            'action': 'test_user_created',
            'email': test_user.email
        }
    )
    
    # Создаем несколько тестовых коллекций
    test_collections = [
        {
            'name': 'Коллекция кроссовок',
            'description': 'Моя коллекция спортивной обуви разных брендов и моделей',
            'is_public': True,
            'custom_fields': [
                {'name': 'Бренд', 'type': 'text', 'required': True},
                {'name': 'Размер', 'type': 'number', 'required': True},
                {'name': 'Цена', 'type': 'number', 'required': False},
                {'name': 'Дата покупки', 'type': 'date', 'required': False},
                {'name': 'Любимые', 'type': 'checkbox', 'required': False}
            ],
            'items': [
                {
                    'name': 'Nike Air Max 90',
                    'custom_data': {
                        'Бренд': 'Nike',
                        'Размер': 42,
                        'Цена': 8500,
                        'Дата покупки': '2024-12-01',
                        'Любимые': True
                    }
                },
                {
                    'name': 'Adidas Ultraboost 22',
                    'custom_data': {
                        'Бренд': 'Adidas',
                        'Размер': 42,
                        'Цена': 12000,
                        'Дата покупки': '2024-11-15',
                        'Любимые': True
                    }
                },
                {
                    'name': 'Converse Chuck Taylor',
                    'custom_data': {
                        'Бренд': 'Converse',
                        'Размер': 42,
                        'Цена': 4500,
                        'Дата покупки': '2024-10-20',
                        'Любимые': False
                    }
                }
            ]
        },
        {
            'name': 'Коллекция книг',
            'description': 'Личная библиотека с любимыми произведениями',
            'is_public': False,
            'custom_fields': [
                {'name': 'Автор', 'type': 'text', 'required': True},
                {'name': 'Жанр', 'type': 'text', 'required': False},
                {'name': 'Год издания', 'type': 'number', 'required': False},
                {'name': 'Рейтинг', 'type': 'number', 'required': False},
                {'name': 'Прочитано', 'type': 'checkbox', 'required': False}
            ],
            'items': [
                {
                    'name': '1984',
                    'custom_data': {
                        'Автор': 'Джордж Оруэлл',
                        'Жанр': 'Антиутопия',
                        'Год издания': 1949,
                        'Рейтинг': 5,
                        'Прочитано': True
                    }
                },
                {
                    'name': 'Мастер и Маргарита',
                    'custom_data': {
                        'Автор': 'Михаил Булгаков',
                        'Жанр': 'Роман',
                        'Год издания': 1967,
                        'Рейтинг': 5,
                        'Прочитано': True
                    }
                }
            ]
        },
        {
            'name': 'Винтажные игрушки',
            'description': 'Коллекция редких игрушек 80-90х годов',
            'is_public': True,
            'custom_fields': [
                {'name': 'Производитель', 'type': 'text', 'required': True},
                {'name': 'Год выпуска', 'type': 'number', 'required': False},
                {'name': 'Состояние', 'type': 'text', 'required': False},
                {'name': 'Цена покупки', 'type': 'number', 'required': False},
                {'name': 'Редкая', 'type': 'checkbox', 'required': False}
            ],
            'items': [
                {
                    'name': 'Трансформер Оптимус Прайм',
                    'custom_data': {
                        'Производитель': 'Hasbro',
                        'Год выпуска': 1984,
                        'Состояние': 'Отличное',
                        'Цена покупки': 15000,
                        'Редкая': True
                    }
                }
            ]
        }
    ]
    
    # Создаем коллекции и их предметы
    for collection_data in test_collections:
        items_data = collection_data.pop('items', [])
        
        collection = Collection(
            user_id=test_user.id,
            **collection_data
        )
        db.session.add(collection)
        db.session.commit()
        
        print(f"✓ Создана коллекция: {collection.name}")
        
        # Логируем создание коллекции
        AuditLogger.log_action(
            action=AuditAction.COLLECTION_CREATE,
            resource_type=ResourceType.COLLECTION,
            resource_id=collection.id,
            user_id=test_user.id,
            details={
                'collection_name': collection.name,
                'is_public': collection.is_public
            }
        )
        
        # Создаем предметы для коллекции
        for item_data in items_data:
            item = Item(
                collection_id=collection.id,
                **item_data
            )
            db.session.add(item)
        
        db.session.commit()
        print(f"  └─ Добавлено предметов: {len(items_data)}")
        
        # Логируем создание предметов
        if items_data:
            AuditLogger.log_action(
                action=AuditAction.ITEM_CREATE,
                resource_type=ResourceType.ITEM,
                resource_id=collection.id,
                user_id=test_user.id,
                details={
                    'collection_name': collection.name,
                    'items_count': len(items_data)
                }
            )
    
    print(f"\n✓ Тестовые данные созданы:")
    print(f"  - Пользователь: {test_user.email}")
    print(f"  - Коллекций: {len(test_collections)}")
    print(f"  - Публичных коллекций: {len([c for c in test_collections if c.get('is_public')])}")


def check_dependencies():
    """Проверка зависимостей"""
    print("=== Проверка зависимостей ===")
    
    required_packages = [
        ('flask', 'Flask'),
        ('flask_sqlalchemy', 'Flask-SQLAlchemy'),
        ('flask_login', 'Flask-Login'),
        ('authlib', 'Authlib'),
        ('pillow', 'Pillow'),
        ('python_dotenv', 'python-dotenv')
    ]
    
    missing_packages = []
    
    for package, display_name in required_packages:
        try:
            __import__(package)
            print(f"✓ {display_name}")
        except ImportError:
            print(f"✗ {display_name} - НЕ УСТАНОВЛЕН")
            missing_packages.append(display_name)
    
    if missing_packages:
        print(f"\nОшибка: Отсутствуют зависимости: {', '.join(missing_packages)}")
        print("Установите их командой: pip install -r requirements.txt")
        return False
    
    print("✓ Все зависимости установлены")
    return True


def check_config():
    """Проверка конфигурации"""
    print("\n=== Проверка конфигурации ===")
    
    try:
        app = create_app()
    except Exception as e:
        print(f"✗ Ошибка создания приложения: {e}")
        return False
    
    with app.app_context():
        # Проверяем настройки OAuth
        if app.config.get('GOOGLE_CLIENT_ID'):
            print("✓ Google OAuth настроен")
        else:
            print("⚠ Google OAuth не настроен (см. .env)")
        
        if app.config.get('APPLE_CLIENT_ID'):
            print("✓ Apple OAuth настроен")
        else:
            print("⚠ Apple OAuth не настроен (см. .env)")
        
        # Проверяем SECRET_KEY
        if app.config.get('SECRET_KEY') == 'dev-key-change-in-production':
            print("⚠ Используется стандартный SECRET_KEY")
        else:
            print("✓ SECRET_KEY настроен")
        
        # Проверяем директорию для загрузок
        upload_folder = app.config.get('UPLOAD_FOLDER')
        if upload_folder:
            if setup_upload_directory(upload_folder):
                print(f"✓ Директория загрузок: {upload_folder}")
            else:
                print(f"⚠ Проблема с директорией загрузок: {upload_folder}")
        
        # Проверяем подключение к БД
        try:
            db.session.execute(db.text('SELECT 1'))
            print("✓ Подключение к базе данных работает")
        except Exception as e:
            print(f"✗ Ошибка подключения к БД: {e}")
            return False
    
    print("✓ Конфигурация проверена")
    return True


def check_security():
    """Проверка безопасности"""
    print("\n=== Проверка безопасности ===")
    
    app = create_app()
    issues = []
    
    with app.app_context():
        # Проверяем SECRET_KEY
        if app.config.get('SECRET_KEY') in ['dev-key-change-in-production', None, '']:
            issues.append("Небезопасный SECRET_KEY")
        
        # Проверяем режим отладки
        if app.debug and os.environ.get('FLASK_ENV') == 'production':
            issues.append("Режим отладки включен в продакшне")
        
        # Проверяем HTTPS в продакшне
        if (os.environ.get('FLASK_ENV') == 'production' and 
            not os.environ.get('FORCE_HTTPS', '').lower() == 'true'):
            issues.append("HTTPS не принудительно включен в продакшне")
        
        # Проверяем права доступа к директорий загрузок
        upload_folder = app.config.get('UPLOAD_FOLDER')
        if upload_folder and os.path.exists(upload_folder):
            stat_info = os.stat(upload_folder)
            if stat_info.st_mode & 0o077:
                issues.append("Небезопасные права доступа к директории загрузок")
    
    if issues:
        print("⚠ Обнаружены проблемы безопасности:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✓ Проблем безопасности не обнаружено")
        return True


def cleanup_database():
    """Очистка тестовых данных"""
    print("\n=== Очистка тестовых данных ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Удаляем тестового пользователя и связанные данные
            test_user = User.query.filter_by(email='test@example.com').first()
            if test_user:
                # Удаляем все коллекции пользователя (каскадно удалятся и предметы)
                collections = Collection.query.filter_by(user_id=test_user.id).all()
                for collection in collections:
                    db.session.delete(collection)
                
                # Удаляем пользователя
                db.session.delete(test_user)
                db.session.commit()
                
                print(f"✓ Удален тестовый пользователь и {len(collections)} коллекций")
                
                # Логируем очистку
                AuditLogger.log_action(
                    action=AuditAction.SYSTEM,
                    resource_type=ResourceType.SYSTEM,
                    details={
                        'action': 'test_data_cleanup',
                        'collections_removed': len(collections)
                    }
                )
            else:
                print("Тестовые данные не найдены")
                
        except Exception as e:
            print(f"✗ Ошибка при очистке: {e}")
            return False
    
    return True


def show_statistics():
    """Показать статистику базы данных"""
    print("\n=== Статистика базы данных ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Статистика пользователей
            total_users = User.query.count()
            active_users = User.query.filter_by(is_active=True).count()
            admin_users = User.query.filter_by(is_admin=True).count()
            
            print(f"Пользователи:")
            print(f"  - Всего: {total_users}")
            print(f"  - Активных: {active_users}")
            print(f"  - Администраторов: {admin_users}")
            
            # Статистика коллекций
            total_collections = Collection.query.count()
            public_collections = Collection.query.filter_by(is_public=True).count()
            
            print(f"Коллекции:")
            print(f"  - Всего: {total_collections}")
            print(f"  - Публичных: {public_collections}")
            print(f"  - Приватных: {total_collections - public_collections}")
            
            # Статистика предметов
            total_items = Item.query.count()
            
            print(f"Предметы:")
            print(f"  - Всего: {total_items}")
            
            if total_collections > 0:
                avg_items = total_items / total_collections
                print(f"  - В среднем на коллекцию: {avg_items:.1f}")
            
            # Статистика аудит-логов
            total_logs = AuditLog.query.count()
            
            print(f"Аудит-логи:")
            print(f"  - Всего записей: {total_logs}")
            
            # Топ действий в аудит-логах
            if total_logs > 0:
                from sqlalchemy import func
                top_actions = (db.session.query(AuditLog.action, func.count(AuditLog.action))
                             .group_by(AuditLog.action)
                             .order_by(func.count(AuditLog.action).desc())
                             .limit(5)
                             .all())
                
                print("  - Топ действий:")
                for action, count in top_actions:
                    print(f"    • {action}: {count}")
            
        except Exception as e:
            print(f"✗ Ошибка при получении статистики: {e}")
            return False
    
    return True


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Инициализация базы данных Collections')
    parser.add_argument('--force', action='store_true', 
                       help='Пересоздать базу данных если она существует')
    parser.add_argument('--sample-data', action='store_true',
                       help='Создать тестовые данные')
    parser.add_argument('--admin', action='store_true',
                       help='Создать администратора')
    parser.add_argument('--check-only', action='store_true',
                       help='Только проверить конфигурацию без создания БД')
    parser.add_argument('--security-check', action='store_true',
                       help='Проверить настройки безопасности')
    parser.add_argument('--cleanup', action='store_true',
                       help='Очистить тестовые данные')
    parser.add_argument('--stats', action='store_true',
                       help='Показать статистику базы данных')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 ИНИЦИАЛИЗАЦИЯ COLLECTIONS")
    print("=" * 60)
    
    # Проверяем зависимости
    if not check_dependencies():
        sys.exit(1)
    
    # Проверяем конфигурацию
    if not check_config():
        sys.exit(1)
    
    # Проверка безопасности
    if args.security_check:
        if not check_security():
            sys.exit(1)
        return
    
    # Только проверки
    if args.check_only:
        check_security()
        print("\n" + "=" * 60)
        print("✅ ВСЕ ПРОВЕРКИ ЗАВЕРШЕНЫ")
        print("=" * 60)
        return
    
    # Очистка данных
    if args.cleanup:
        if cleanup_database():
            print("\n✅ Очистка завершена успешно")
        else:
            sys.exit(1)
        return
    
    # Показать статистику
    if args.stats:
        show_statistics()
        return
    
    # Инициализируем базу данных
    try:
        success = init_database(
            force=args.force, 
            sample_data=args.sample_data,
            create_admin_user=args.admin
        )
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
            print("=" * 60)
            
            print("\n📋 Что дальше:")
            print("1. Для запуска приложения:")
            print("   cd backend && python run.py")
            print("\n2. Приложение будет доступно:")
            print("   http://localhost:5000")
            
            if args.sample_data:
                print("\n3. 🧪 Тестовые данные:")
                print("   Email: test@example.com")
                print("   Коллекции: 'Коллекция кроссовок' (публичная)")
                print("              'Коллекция книг' (приватная)")
                print("              'Винтажные игрушки' (публичная)")
            
            if args.admin:
                print("\n4. 👨‍💼 Панель администратора:")
                print("   /admin (после входа под админ-аккаунтом)")
            
            print("\n5. 📚 Полезные команды:")
            print("   python init_db.py --stats          # Статистика БД")
            print("   python init_db.py --security-check # Проверка безопасности")
            print("   python init_db.py --cleanup        # Очистка тестовых данных")
            print("   flask shell                        # Интерактивная оболочка")
            
            print("\n" + "=" * 60)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Операция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        print("\nПодробности ошибки:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()