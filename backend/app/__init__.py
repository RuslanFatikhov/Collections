import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from app.config.config import config

# Инициализация расширений
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

# Попытка импорта CSRF, если не получается - работаем без него
try:
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()
    CSRF_AVAILABLE = True
except ImportError:
    csrf = None
    CSRF_AVAILABLE = False

def create_app(config_name=None):
    """Фабрика приложений Flask"""
    
    # Создание экземпляра приложения
    app = Flask(__name__, 
                template_folder='../../frontend/templates',
                static_folder='../../frontend/static')
    
    # Определение конфигурации
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    # Загрузка конфигурации
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Инициализация расширений
    db.init_app(app)
    mail.init_app(app)
    
    # Настройка Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
    login_manager.login_message_category = 'info'
    
    # Настройка CSRF (отключаем для API endpoints)
    if CSRF_AVAILABLE:
        csrf.init_app(app)
        
        # Отключаем CSRF для API маршрутов
        @csrf.exempt
        def exempt_api_routes():
            return request.path.startswith('/api/')
    else:
        app.logger.warning("CSRF protection disabled due to compatibility issues")
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))
    
    # Регистрация Blueprint'ов
    from app.views.auth import auth_bp
    from app.views.collections import collections_bp
    from app.views.api import api_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(collections_bp, url_prefix='/collections')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Главная страница и основные маршруты
    @app.route('/')
    def index():
        from flask import render_template
        from app.models.collection import Collection
        # Получаем последние публичные коллекции для главной страницы
        recent_collections = Collection.query.filter_by(
            is_public=True, 
            is_blocked=False
        ).order_by(Collection.created_at.desc()).limit(6).all()
        return render_template('index.html', recent_collections=recent_collections)
    
    @app.route('/collection/<uuid>')
    def view_collection(uuid):
        """Просмотр публичной коллекции по UUID"""
        from flask import render_template, abort
        from flask_login import current_user
        from app.models.collection import Collection
        
        collection = Collection.query.filter_by(uuid=uuid).first()
        
        if not collection:
            abort(404)
        
        # Проверяем, заблокирована ли коллекция
        if collection.is_blocked:
            abort(403)
        
        # Проверяем доступ к коллекции
        if not collection.is_public and (not current_user.is_authenticated or current_user.id != collection.user_id):
            abort(403)
        
        return render_template('collection_view.html', 
                             collection=collection,
                             items=collection.items,
                             custom_fields=collection.get_custom_fields())
    
    # Middleware для CORS
    @app.after_request
    def after_request(response):
        origins = app.config.get('CORS_ORIGINS', ['*'])
        origin = request.headers.get('Origin')
        
        if origin in origins or '*' in origins:
            response.headers.add('Access-Control-Allow-Origin', origin or '*')
            response.headers.add('Access-Control-Allow-Headers', 
                               'Content-Type,Authorization,X-CSRFToken')
            response.headers.add('Access-Control-Allow-Methods', 
                               'GET,PUT,POST,DELETE,OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
        
        return response
    
    # Обработка preflight запросов
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = jsonify({'status': 'ok'})
            origins = app.config.get('CORS_ORIGINS', ['*'])
            origin = request.headers.get('Origin')
            
            if origin in origins or '*' in origins:
                response.headers.add('Access-Control-Allow-Origin', origin or '*')
                response.headers.add('Access-Control-Allow-Headers', 
                                   'Content-Type,Authorization,X-CSRFToken')
                response.headers.add('Access-Control-Allow-Methods', 
                                   'GET,PUT,POST,DELETE,OPTIONS')
                response.headers.add('Access-Control-Allow-Credentials', 'true')
            
            return response
    
    # Обработка ошибок
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Ресурс не найден'}), 404
        from flask import render_template
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Внутренняя ошибка сервера'}), 500
        from flask import render_template
        return render_template('500.html'), 500
    
    @app.errorhandler(413)
    def file_too_large_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Файл слишком большой. Максимальный размер: 10MB'}), 413
        from flask import flash, redirect, url_for
        flash('Файл слишком большой. Максимальный размер: 10MB', 'error')
        return redirect(url_for('index'))
    
    @app.errorhandler(400)
    def bad_request_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Неверный запрос'}), 400
        from flask import render_template
        return render_template('400.html'), 400
    
    @app.errorhandler(403)
    def forbidden_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Доступ запрещен'}), 403
        from flask import render_template
        return render_template('403.html'), 403
    
    # Обработчик для неавторизованных пользователей
    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Необходима авторизация'}), 401
        from flask import flash, redirect, url_for
        flash('Пожалуйста, войдите в систему для доступа к этой странице.', 'info')
        return redirect(url_for('auth.login', next=request.url))
    
    # Создание таблиц базы данных
    with app.app_context():
        # Импортируем модели для создания таблиц
        from app.models.user import User
        from app.models.collection import Collection
        from app.models.item import Item
        
        db.create_all()
        
        # Создаем администратора если указан в переменных окружения
        admin_email = os.environ.get('ADMIN_EMAIL')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        
        if admin_email and admin_password:
            admin_user = User.query.filter_by(email=admin_email).first()
            if not admin_user:
                admin_user = User.create_user(
                    name=os.environ.get('ADMIN_NAME', 'Administrator'),
                    email=admin_email,
                    password=admin_password
                )
                admin_user.is_admin = True
                admin_user.email_verified = True
                db.session.add(admin_user)
                db.session.commit()
                app.logger.info(f'Created admin user: {admin_email}')
    
    # Логирование запуска приложения
    app.logger.info('Collections application startup complete')
    
    return app