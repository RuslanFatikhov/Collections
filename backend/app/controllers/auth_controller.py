import requests
import jwt
import time
from datetime import datetime
from flask import session, current_app, url_for, request
from flask_login import login_user, logout_user, current_user
from app import db
from app.models.user import User
from app.models.audit_log import AuditAction, ResourceType
from app.config.oauth import get_oauth_config, generate_state, validate_provider
from app.utils.logger import AuditLogger
from app.utils.security import SecurityValidator, sanitize_html
from app.utils.rate_limiter import auth_rate_limit

class AuthController:
    """Контроллер для обработки аутентификации через OAuth"""
    
    @staticmethod
    @auth_rate_limit()
    def initiate_login(provider):
        """Инициация процесса OAuth авторизации"""
        try:
            # Логируем попытку входа
            AuditLogger.log_action(
                action=AuditAction.LOGIN,
                resource_type=ResourceType.AUTH,
                details={'provider': provider, 'step': 'initiate'}
            )
            
            # Проверяем поддержку провайдера
            if not validate_provider(provider):
                AuditLogger.log_action(
                    action=AuditAction.LOGIN_FAILED,
                    resource_type=ResourceType.AUTH,
                    details={'provider': provider, 'error': 'unsupported_provider'}
                )
                return {'error': f'Неподдерживаемый провайдер: {provider}'}, 400
            
            # Очищаем предыдущие данные сессии для безопасности
            AuthController._clear_oauth_session()
            
            # Получаем конфигурацию OAuth
            oauth_config = get_oauth_config(provider)
            
            # Генерируем state для защиты от CSRF
            state = generate_state()
            session['oauth_state'] = state
            session['oauth_provider'] = provider
            session['oauth_timestamp'] = int(time.time())  # Для проверки времени жизни
            
            # Получаем URL для авторизации
            auth_url = oauth_config.get_authorization_url(state)
            
            current_app.logger.info(f'OAuth login initiated for provider: {provider}')
            
            return {'auth_url': auth_url}, 200
            
        except Exception as e:
            current_app.logger.error(f'Ошибка при инициации OAuth {provider}: {str(e)}')
            AuditLogger.log_action(
                action=AuditAction.LOGIN_FAILED,
                resource_type=ResourceType.AUTH,
                details={'provider': provider, 'error': 'system_error', 'message': str(e)}
            )
            return {'error': 'Ошибка при инициации авторизации'}, 500
    
    @staticmethod
    @auth_rate_limit()
    def handle_oauth_callback(provider, code, state, user_data=None):
        """Обработка callback от OAuth провайдера"""
        try:
            # Валидация входных параметров
            if not code or not state:
                AuditLogger.log_action(
                    action=AuditAction.LOGIN_FAILED,
                    resource_type=ResourceType.AUTH,
                    details={'provider': provider, 'error': 'missing_parameters'}
                )
                return {'error': 'Отсутствуют обязательные параметры'}, 400
            
            # Проверяем state для защиты от CSRF
            if not AuthController._validate_state(state):
                AuditLogger.log_action(
                    action=AuditAction.LOGIN_FAILED,
                    resource_type=ResourceType.AUTH,
                    details={'provider': provider, 'error': 'invalid_state'}
                )
                return {'error': 'Неверный state параметр'}, 400
            
            # Проверяем провайдера
            if session.get('oauth_provider') != provider:
                AuditLogger.log_action(
                    action=AuditAction.LOGIN_FAILED,
                    resource_type=ResourceType.AUTH,
                    details={'provider': provider, 'error': 'provider_mismatch'}
                )
                return {'error': 'Неверный провайдер'}, 400
            
            # Проверяем время жизни OAuth сессии (максимум 10 минут)
            oauth_timestamp = session.get('oauth_timestamp', 0)
            if int(time.time()) - oauth_timestamp > 600:
                AuthController._clear_oauth_session()
                AuditLogger.log_action(
                    action=AuditAction.LOGIN_FAILED,
                    resource_type=ResourceType.AUTH,
                    details={'provider': provider, 'error': 'session_expired'}
                )
                return {'error': 'Сессия OAuth истекла'}, 400
            
            # Получаем конфигурацию OAuth
            oauth_config = get_oauth_config(provider)
            
            # Обмениваем код на токен
            token_data = AuthController._exchange_code_for_token(oauth_config, code, provider)
            if not token_data:
                AuditLogger.log_action(
                    action=AuditAction.LOGIN_FAILED,
                    resource_type=ResourceType.AUTH,
                    details={'provider': provider, 'error': 'token_exchange_failed'}
                )
                return {'error': 'Ошибка получения токена'}, 400
            
            # Получаем данные пользователя
            if provider == 'google':
                user_info = AuthController._get_google_user_info(token_data['access_token'])
            elif provider == 'apple':
                user_info = AuthController._get_apple_user_info(token_data, user_data)
            else:
                AuditLogger.log_action(
                    action=AuditAction.LOGIN_FAILED,
                    resource_type=ResourceType.AUTH,
                    details={'provider': provider, 'error': 'unsupported_provider'}
                )
                return {'error': 'Неподдерживаемый провайдер'}, 400
            
            if not user_info:
                AuditLogger.log_action(
                    action=AuditAction.LOGIN_FAILED,
                    resource_type=ResourceType.AUTH,
                    details={'provider': provider, 'error': 'user_info_failed'}
                )
                return {'error': 'Ошибка получения данных пользователя'}, 400
            
            # Валидируем данные пользователя
            if not AuthController._validate_user_info(user_info):
                AuditLogger.log_action(
                    action=AuditAction.LOGIN_FAILED,
                    resource_type=ResourceType.AUTH,
                    details={'provider': provider, 'error': 'invalid_user_data'}
                )
                return {'error': 'Некорректные данные пользователя'}, 400
            
            # Создаем или обновляем пользователя
            user = AuthController._create_or_update_user(provider, user_info)
            if not user:
                AuditLogger.log_action(
                    action=AuditAction.LOGIN_FAILED,
                    resource_type=ResourceType.AUTH,
                    details={'provider': provider, 'error': 'user_creation_failed'}
                )
                return {'error': 'Ошибка создания пользователя'}, 500
            
            # Авторизуем пользователя
            login_user(user, remember=True)
            
            # Логируем успешный вход
            AuditLogger.log_auth_attempt(
                success=True,
                user_id=user.id,
                email=user.email,
                provider=provider
            )
            
            # Очищаем сессию
            AuthController._clear_oauth_session()
            
            current_app.logger.info(f'User {user.email} successfully logged in via {provider}')
            
            return {'success': True, 'user': user.to_dict()}, 200
            
        except Exception as e:
            current_app.logger.error(f'Ошибка в OAuth callback {provider}: {str(e)}')
            AuditLogger.log_action(
                action=AuditAction.LOGIN_FAILED,
                resource_type=ResourceType.AUTH,
                details={'provider': provider, 'error': 'system_error', 'message': str(e)}
            )
            return {'error': 'Ошибка авторизации'}, 500
    
    @staticmethod
    def logout():
        """Выход пользователя из системы"""
        try:
            user_id = current_user.id if current_user.is_authenticated else None
            user_email = current_user.email if current_user.is_authenticated else None
            
            # Выходим из системы
            logout_user()
            
            # Очищаем OAuth сессию
            AuthController._clear_oauth_session()
            
            # Логируем выход
            AuditLogger.log_action(
                action=AuditAction.LOGOUT,
                resource_type=ResourceType.AUTH,
                user_id=user_id
            )
            
            current_app.logger.info(f'User {user_email} logged out')
            
            return {'success': True}, 200
            
        except Exception as e:
            current_app.logger.error(f'Ошибка при выходе: {str(e)}')
            return {'error': 'Ошибка при выходе'}, 500
    
    @staticmethod
    def _validate_state(state):
        """Проверка state параметра"""
        session_state = session.get('oauth_state')
        if not session_state or not state:
            return False
        
        # Проверяем что state соответствует и имеет правильную длину
        return (session_state == state and 
                len(state) >= 32 and  # Минимальная длина для безопасности
                all(c.isalnum() for c in state))  # Только буквы и цифры
    
    @staticmethod
    def _validate_user_info(user_info):
        """Валидация данных пользователя от OAuth провайдера"""
        if not isinstance(user_info, dict):
            return False
        
        # Проверяем обязательные поля
        if not user_info.get('id') or not user_info.get('email'):
            return False
        
        # Валидируем email
        is_valid_email, _ = SecurityValidator.validate_email(user_info['email'])
        if not is_valid_email:
            return False
        
        # Очищаем и валидируем имя пользователя
        if user_info.get('name'):
            user_info['name'] = sanitize_html(user_info['name'])
            is_valid_name, _ = SecurityValidator.validate_text(
                user_info['name'], 1, 100, "Name"
            )
            if not is_valid_name:
                user_info['name'] = user_info['email'].split('@')[0]  # Fallback
        
        return True
    
    @staticmethod
    def _exchange_code_for_token(oauth_config, code, provider):
        """Обмен authorization code на access token"""
        try:
            data = {
                'grant_type': 'authorization_code',
                'client_id': oauth_config.client_id,
                'client_secret': oauth_config.client_secret,
                'redirect_uri': oauth_config.redirect_uri,
                'code': code
            }
            
            # Для Apple ID нужна специальная обработка
            if provider == 'apple':
                data['client_secret'] = AuthController._generate_apple_client_secret(oauth_config)
            
            # Устанавливаем timeout для безопасности
            response = requests.post(
                oauth_config.token_url, 
                data=data,
                timeout=30,  # 30 секунд timeout
                headers={'User-Agent': 'Collections-App/1.0'}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Проверяем что получили необходимые токены
                if not token_data.get('access_token'):
                    current_app.logger.error(f'No access token in response from {provider}')
                    return None
                
                return token_data
            else:
                current_app.logger.error(f'Token exchange failed for {provider}: {response.status_code} {response.text}')
                return None
                
        except requests.exceptions.Timeout:
            current_app.logger.error(f'Timeout during token exchange for {provider}')
            return None
        except Exception as e:
            current_app.logger.error(f'Error exchanging code for token ({provider}): {str(e)}')
            return None
    
    @staticmethod
    def _get_google_user_info(access_token):
        """Получение информации о пользователе от Google"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'User-Agent': 'Collections-App/1.0'
            }
            
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем обязательные поля
                if not data.get('id') or not data.get('email'):
                    current_app.logger.error('Missing required fields in Google user info')
                    return None
                
                return {
                    'id': str(data.get('id')),  # Приводим к строке для единообразия
                    'email': data.get('email'),
                    'name': data.get('name', data.get('email', '').split('@')[0]),
                    'avatar_url': data.get('picture')
                }
            else:
                current_app.logger.error(f'Google userinfo failed: {response.status_code} {response.text}')
                return None
                
        except requests.exceptions.Timeout:
            current_app.logger.error('Timeout getting Google user info')
            return None
        except Exception as e:
            current_app.logger.error(f'Error getting Google user info: {str(e)}')
            return None
    
    @staticmethod
    def _get_apple_user_info(token_data, user_data):
        """Получение информации о пользователе от Apple"""
        try:
            # Apple возвращает информацию в JWT токене
            id_token = token_data.get('id_token')
            if not id_token:
                current_app.logger.error('No id_token in Apple response')
                return None
            
            # Декодируем JWT (без верификации для упрощения, в продакшене нужна верификация)
            try:
                decoded_token = jwt.decode(id_token, options={"verify_signature": False})
            except jwt.InvalidTokenError as e:
                current_app.logger.error(f'Invalid Apple ID token: {str(e)}')
                return None
            
            # Проверяем обязательные поля
            if not decoded_token.get('sub') or not decoded_token.get('email'):
                current_app.logger.error('Missing required fields in Apple ID token')
                return None
            
            user_info = {
                'id': str(decoded_token.get('sub')),
                'email': decoded_token.get('email'),
                'name': None,
                'avatar_url': None
            }
            
            # Apple может передать дополнительные данные пользователя при первой авторизации
            if user_data and isinstance(user_data, dict):
                name_data = user_data.get('name', {})
                if isinstance(name_data, dict):
                    first_name = sanitize_html(name_data.get('firstName', ''))
                    last_name = sanitize_html(name_data.get('lastName', ''))
                    user_info['name'] = f"{first_name} {last_name}".strip()
            
            # Если имя не получено, используем email
            if not user_info['name']:
                user_info['name'] = user_info['email'].split('@')[0] if user_info['email'] else 'Apple User'
            
            return user_info
            
        except Exception as e:
            current_app.logger.error(f'Error getting Apple user info: {str(e)}')
            return None
    
    @staticmethod
    def _generate_apple_client_secret(oauth_config):
        """Генерация client_secret для Apple ID (JWT)"""
        try:
            # Проверяем наличие необходимых параметров
            if not all([oauth_config.private_key, oauth_config.team_id, oauth_config.key_id]):
                current_app.logger.error('Missing Apple OAuth configuration')
                return None
            
            # Читаем приватный ключ
            try:
                with open(oauth_config.private_key, 'r') as key_file:
                    private_key = key_file.read()
            except FileNotFoundError:
                current_app.logger.error(f'Apple private key file not found: {oauth_config.private_key}')
                return None
            
            # Создаем JWT payload
            now = int(time.time())
            payload = {
                'iss': oauth_config.team_id,
                'iat': now,
                'exp': now + 3600,  # 1 час
                'aud': 'https://appleid.apple.com',
                'sub': oauth_config.client_id
            }
            
            # Создаем JWT headers
            headers = {
                'kid': oauth_config.key_id,
                'alg': 'ES256'
            }
            
            # Генерируем JWT
            client_secret = jwt.encode(payload, private_key, algorithm='ES256', headers=headers)
            return client_secret
            
        except Exception as e:
            current_app.logger.error(f'Error generating Apple client secret: {str(e)}')
            return None
    
    @staticmethod
    def _create_or_update_user(provider, user_info):
        """Создание или обновление пользователя в базе данных"""
        try:
            user = None
            is_new_user = False
            
            # Ищем пользователя по provider ID
            if provider == 'google':
                user = User.find_by_google_id(user_info['id'])
            elif provider == 'apple':
                user = User.find_by_apple_id(user_info['id'])
            
            # Если пользователь не найден по provider ID, ищем по email
            if not user and user_info.get('email'):
                user = User.find_by_email(user_info['email'])
                
                # Если найден по email, обновляем provider ID
                if user:
                    if provider == 'google':
                        user.google_id = user_info['id']
                    elif provider == 'apple':
                        user.apple_id = user_info['id']
                    
                    AuditLogger.log_action(
                        action=AuditAction.USER_UPDATE,
                        resource_type=ResourceType.USER,
                        resource_id=user.id,
                        user_id=user.id,
                        details={'action': 'linked_oauth_provider', 'provider': provider}
                    )
            
            # Если пользователь все еще не найден, создаем нового
            if not user:
                user = User()
                is_new_user = True
                
                if provider == 'google':
                    user.google_id = user_info['id']
                elif provider == 'apple':
                    user.apple_id = user_info['id']
                
                db.session.add(user)
            
            # Обновляем данные пользователя
            user.name = user_info.get('name', user.name or 'Пользователь')
            user.email = user_info.get('email', user.email)
            
            # Обновляем аватар только если его нет или если это новый пользователь
            if user_info.get('avatar_url') and (not user.avatar_url or is_new_user):
                user.avatar_url = user_info['avatar_url']
            
            user.updated_at = datetime.utcnow()
            
            # Сохраняем изменения
            db.session.commit()
            
            # Логируем создание нового пользователя
            if is_new_user:
                AuditLogger.log_action(
                    action=AuditAction.USER_CREATE,
                    resource_type=ResourceType.USER,
                    resource_id=user.id,
                    user_id=user.id,
                    details={'provider': provider, 'email': user.email}
                )
            
            current_app.logger.info(f'User {user.email} {"created" if is_new_user else "updated"} via {provider}')
            return user
            
        except Exception as e:
            current_app.logger.error(f'Error creating/updating user: {str(e)}')
            db.session.rollback()
            return None
    
    @staticmethod
    def _clear_oauth_session():
        """Очистка OAuth данных из сессии"""
        session.pop('oauth_state', None)
        session.pop('oauth_provider', None)
        session.pop('oauth_timestamp', None)