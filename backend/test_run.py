#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    app = create_app()
    
    print("✓ Приложение создано успешно")
    print(f"✓ База данных: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    print(f"✓ Debug режим: {app.debug}")
    
    # Запускаем сервер
    app.run(host='127.0.0.1', port=5000, debug=True)
    
except Exception as e:
    print(f"✗ Ошибка: {str(e)}")
    import traceback
    traceback.print_exc()
