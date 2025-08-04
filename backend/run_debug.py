import traceback
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
    
    from app import create_app
    app = create_app()
    
    print("✅ Приложение создано успешно")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    traceback.print_exc()
