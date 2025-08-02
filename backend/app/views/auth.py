from flask import Blueprint, request, redirect, url_for, render_template, flash, jsonify, session
from flask_login import current_user, logout_user
from app.controllers.auth_controller import AuthController
from app.config.oauth import get_configured_providers, validate_provider

# Создание Blueprint для аутентификации
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    """Страница входа в систему"""
    # Если пользователь уже авторизован, перенаправляем на главную
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Получаем список настроенных OAuth провайдеров
    providers = get_configured_providers()
    
    return render_template('login.html', providers=providers)

@auth_bp.route('/login/<provider>')
def initiate_oauth_login(provider):
    """Инициация OAuth авторизации для указанного провайдера"""
    
    # Проверяем, что пользователь не авторизован
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Проверяем поддержку провайдера
    if not validate_provider(provider):
        flash(f'Неподдерживаемый провайдер авторизации: {provider}', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        # Инициируем процесс OAuth
        result, status_code = AuthController.initiate_login(provider)
        
        if status_code == 200:
            # Перенаправляем пользователя на страницу авторизации провайдера
            return redirect(result['auth_url'])
        else:
            flash(result.get('error', 'Ошибка при авторизации'), 'error')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        flash('Произошла ошибка при авторизации. Попробуйте позже.', 'error')
        return redirect(url_for('auth.login'))

@auth_bp.route('/callback/<provider>', methods=['GET', 'POST'])
def oauth_callback(provider):
    """Обработка callback от OAuth провайдера"""
    
    try:
        # Получаем параметры из запроса
        if request.method == 'POST':
            # Apple ID использует POST для callback
            code = request.form.get('code')
            state = request.form.get('state')
            error = request.form.get('error')
            user_data = request.form.get('user')  # Apple может передать дополнительные данные
            
            # Парсим user_data если есть
            if user_data:
                import json
                try:
                    user_data = json.loads(user_data)
                except:
                    user_data = None
        else:
            # Google использует GET для callback
            code = request.args.get('code')
            state = request.args.get('state')
            error = request.args.get('error')
            user_data = None
        
        # Проверяем на ошибки от провайдера
        if error:
            error_description = request.args.get('error_description', 'Неизвестная ошибка')
            flash(f'Ошибка авторизации: {error_description}', 'error')
            return redirect(url_for('auth.login'))
        
        # Проверяем наличие кода авторизации
        if not code:
            flash('Не получен код авторизации', 'error')
            return redirect(url_for('auth.login'))
        
        # Обрабатываем callback через контроллер
        result, status_code = AuthController.handle_oauth_callback(provider, code, state, user_data)
        
        if status_code == 200:
            # Успешная авторизация
            user_name = result['user'].get('name', 'Пользователь')
            flash(f'Добро пожаловать, {user_name}!', 'success')
            
            # Перенаправляем на страницу, с которой пришел пользователь, или на главную
            next_page = session.get('next_page') or url_for('index')
            session.pop('next_page', None)
            return redirect(next_page)
        else:
            # Ошибка авторизации
            error_message = result.get('error', 'Ошибка при авторизации')
            flash(error_message, 'error')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        flash('Произошла ошибка при обработке авторизации', 'error')
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    """Выход из системы"""
    
    try:
        # Выполняем выход через контроллер
        result, status_code = AuthController.logout()
        
        if status_code == 200:
            flash('Вы успешно вышли из системы', 'info')
        else:
            flash('Ошибка при выходе из системы', 'error')
            
    except Exception as e:
        flash('Произошла ошибка при выходе', 'error')
    
    return redirect(url_for('index'))

# API endpoints для AJAX запросов

@auth_bp.route('/api/login/<provider>')
def api_initiate_oauth_login(provider):
    """API endpoint для инициации OAuth (для AJAX запросов)"""
    
    if current_user.is_authenticated:
        return jsonify({'error': 'Пользователь уже авторизован'}), 400
    
    if not validate_provider(provider):
        return jsonify({'error': f'Неподдерживаемый провайдер: {provider}'}), 400
    
    result, status_code = AuthController.initiate_login(provider)
    return jsonify(result), status_code

@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    """API endpoint для выхода из системы (для AJAX запросов)"""
    
    result, status_code = AuthController.logout()
    return jsonify(result), status_code

@auth_bp.route('/api/user')
def api_current_user():
    """API endpoint для получения информации о текущем пользователе"""
    
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': current_user.to_dict()
        }), 200
    else:
        return jsonify({
            'authenticated': False,
            'user': None
        }), 200

@auth_bp.route('/api/providers')
def api_oauth_providers():
    """API endpoint для получения списка доступных OAuth провайдеров"""
    
    providers = get_configured_providers()
    return jsonify({'providers': providers}), 200

# Обработчик перед запросом для сохранения страницы перенаправления
@auth_bp.before_app_request
def before_request():
    """Сохраняем страницу, с которой пришел неавторизованный пользователь"""
    
    # Список страниц, требующих авторизации
    protected_endpoints = ['profile', 'collections.create_collection', 'collections.edit_collection']
    
    if (request.endpoint in protected_endpoints and 
        not current_user.is_authenticated and 
        request.method == 'GET'):
        session['next_page'] = request.url

# Контекстный процессор для передачи OAuth провайдеров в шаблоны
@auth_bp.app_context_processor
def inject_oauth_providers():
    """Добавляем список OAuth провайдеров в контекст шаблонов"""
    return {
        'oauth_providers': get_configured_providers()
    }

# Обработчики ошибок для Blueprint

@auth_bp.errorhandler(400)
def auth_bad_request(error):
    """Обработка ошибки 400 в auth blueprint"""
    if request.path.startswith('/auth/api/'):
        return jsonify({'error': 'Неверный запрос'}), 400
    flash('Неверный запрос', 'error')
    return redirect(url_for('auth.login'))

@auth_bp.errorhandler(500)
def auth_internal_error(error):
    """Обработка ошибки 500 в auth blueprint"""
    if request.path.startswith('/auth/api/'):
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500
    flash('Произошла внутренняя ошибка. Попробуйте позже.', 'error')
    return redirect(url_for('auth.login'))