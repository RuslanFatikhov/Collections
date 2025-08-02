import os
from urllib.parse import urlencode
import secrets
import string

class OAuthConfig:
    """Базовый класс для конфигурации OAuth провайдеров"""
    
    def __init__(self):
        self.client_id = None
        self.client_secret = None
        self.redirect_uri = None
        self.scope = []
        self.authorize_url = None
        self.token_url = None
        self.userinfo_url = None

class GoogleOAuthConfig(OAuthConfig):
    """Конфигурация для Google OAuth"""
    
    def __init__(self):
        super().__init__()
        self.client_id = os.environ.get('GOOGLE_CLIENT_ID')
        self.client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/callback/google')
        
        # Google OAuth URLs
        self.authorize_url = 'https://accounts.google.com/o/oauth2/v2/auth'
        self.token_url = 'https://oauth2.googleapis.com/token'
        self.userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        
        # Scopes для получения базовой информации о пользователе
        self.scope = [
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
    
    def get_authorization_url(self, state):
        """Получить URL для авторизации через Google"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scope),
            'response_type': 'code',
            'state': state,
            'access_type': 'offline',
            'prompt': 'consent'
        }
        return f"{self.authorize_url}?{urlencode(params)}"

class AppleOAuthConfig(OAuthConfig):
    """Конфигурация для Apple ID OAuth"""
    
    def __init__(self):
        super().__init__()
        self.client_id = os.environ.get('APPLE_CLIENT_ID')  # Service ID
        self.team_id = os.environ.get('APPLE_TEAM_ID')
        self.key_id = os.environ.get('APPLE_KEY_ID')
        self.private_key = os.environ.get('APPLE_PRIVATE_KEY')  # Путь к файлу .p8
        self.redirect_uri = os.environ.get('APPLE_REDIRECT_URI', 'http://localhost:5000/auth/callback/apple')
        
        # Apple OAuth URLs
        self.authorize_url = 'https://appleid.apple.com/auth/authorize'
        self.token_url = 'https://appleid.apple.com/auth/token'
        self.userinfo_url = None  # Apple не предоставляет отдельный userinfo endpoint
        
        # Scopes для Apple ID
        self.scope = ['name', 'email']
    
    def get_authorization_url(self, state):
        """Получить URL для авторизации через Apple ID"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scope),
            'response_type': 'code',
            'state': state,
            'response_mode': 'form_post'  # Apple рекомендует form_post для веб-приложений
        }
        return f"{self.authorize_url}?{urlencode(params)}"

# Инициализация конфигураций
google_oauth = GoogleOAuthConfig()
apple_oauth = AppleOAuthConfig()

# Словарь провайдеров для удобного доступа
OAUTH_PROVIDERS = {
    'google': google_oauth,
    'apple': apple_oauth
}

def generate_state():
    """Генерация случайного state параметра для защиты от CSRF"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

def validate_provider(provider):
    """Проверка что провайдер поддерживается"""
    return provider in OAUTH_PROVIDERS

def get_oauth_config(provider):
    """Получить конфигурацию OAuth для указанного провайдера"""
    if not validate_provider(provider):
        raise ValueError(f"Неподдерживаемый OAuth провайдер: {provider}")
    
    return OAUTH_PROVIDERS[provider]

def is_oauth_configured(provider):
    """Проверить что OAuth провайдер правильно настроен"""
    if not validate_provider(provider):
        return False
    
    config = OAUTH_PROVIDERS[provider]
    
    if provider == 'google':
        return bool(config.client_id and config.client_secret)
    elif provider == 'apple':
        return bool(config.client_id and config.team_id and config.key_id and config.private_key)
    
    return False

def get_configured_providers():
    """Получить список настроенных OAuth провайдеров"""
    configured = []
    for provider in OAUTH_PROVIDERS.keys():
        if is_oauth_configured(provider):
            configured.append(provider)
    return configured