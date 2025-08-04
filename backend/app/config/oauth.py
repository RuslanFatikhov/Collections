# Заглушка для совместимости - OAuth удален
# Этот файл можно удалить после обновления всех импортов

def get_configured_providers():
    """Возвращает пустой список провайдеров"""
    return []

def validate_provider(provider):
    """OAuth провайдеры отключены"""
    return False

def get_oauth_config(provider):
    """OAuth конфигурация недоступна"""
    return None

def generate_state():
    """Генерация state для OAuth (не используется)"""
    return ""

# Добавляем пустой класс для совместимости
class OAuthConfig:
    def __init__(self):
        pass