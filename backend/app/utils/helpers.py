from flask import Blueprint, request, redirect, url_for, render_template, flash, jsonify, session
from flask_login import current_user, login_required
from app.controllers.auth_controller import AuthController
from app.forms.auth import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm, ProfileForm, ChangePasswordForm

# Создание Blueprint для аутентификации
auth_bp = Blueprint('auth', __name__)

# ========== СТРАНИЦЫ АУТЕНТИФИКАЦИИ ==========

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа в систему"""
    # Если пользователь уже авторизован, перенаправляем на главную
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            # Обрабатываем вход через контроллер
            result, status_code = AuthController.login({
                'email': form.email.data,
                'password': form.password.data,
                'remember_me': form.remember_me.data
            })
            
            if status_code == 200:
                # Успешная авторизация
                user_name = result['user'].get('name', 'Пользователь')
                flash(f'Добро пожаловать, {user_name}!', 'success')
                
                # Перенаправляем на страницу, с которой пришел пользователь, или на главную
                next_page = request.args.get('next') or session.get('next_page') or url_for('index')
                session.pop('next_page', None)
                return redirect(next_page)
            else:
                # Ошибка авторизации
                flash(result.get('error', 'Ошибка при входе'), 'error')
        else:
            # Ошибки валидации формы
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{error}', 'error')
    
    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    # Если пользователь уже авторизован, перенаправляем на главную
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegisterForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            # Обрабатываем регистрацию через контроллер
            result, status_code = AuthController.register({
                'name': form.name.data,
                'email': form.email.data,
                'password': form.password.data,
                'password_confirm': form.password_confirm.data
            })
            
            if status_code == 201:
                # Успешная регистрация
                flash(result.get('message', 'Регистрация прошла успешно'), 'success')
                return redirect(url_for('auth.login'))
            else:
                # Ошибка регистрации
                flash(result.get('error', 'Ошибка при регистрации'), 'error')
        else:
            # Ошибки валидации формы
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{error}', 'error')
    
    return render_template('register.html', form=form)

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Верификация email по токену"""
    result, status_code = AuthController.verify_email(token)
    
    if status_code == 200:
        flash(result.get('message', 'Email успешно подтвержден'), 'success')
        return redirect(url_for('auth.login'))
    else:
        flash(result.get('error', 'Ошибка при подтверждении email'), 'error')
        return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Страница восстановления пароля"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = ForgotPasswordForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            # Обрабатываем запрос восстановления через контроллер
            result, status_code = AuthController.forgot_password({
                'email': form.email.data
            })
            
            # Всегда показываем успех для безопасности
            flash(result.get('message', 'Инструкция отправлена на email'), 'info')
            return redirect(url_for('auth.login'))
        else:
            # Ошибки валидации формы
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{error}', 'error')
    
    return render_template('forgot_password.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_form(token):
    """Страница сброса пароля"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = ResetPasswordForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            # Обрабатываем сброс пароля через контроллер
            result, status_code = AuthController.reset_password(token, {
                'password': form.password.data,
                'password_confirm': form.password_confirm.data
            })
            
            if status_code == 200:
                flash(result.get('message', 'Пароль успешно изменен'), 'success')
                return redirect(url_for('auth.login'))
            else:
                flash(result.get('error', 'Ошибка при смене пароля'), 'error')
        else:
            # Ошибки валидации формы
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{error}', 'error')
    
    return render_template('reset_password.html', form=form, token=token)

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

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Страница профиля пользователя"""
    profile_form = ProfileForm(current_user)
    password_form = ChangePasswordForm(current_user)
    
    # Заполняем форму текущими данными
    if request.method == 'GET':
        profile_form.name.data = current_user.name
        profile_form.email.data = current_user.email
    
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'profile' and profile_form.validate_on_submit():
            # Обновляем профиль
            success = current_user.update_profile({
                'name': profile_form.name.data,
                'email': profile_form.email.data
            })
            
            if success:
                flash('Профиль успешно обновлен', 'success')
            else:
                flash('Ошибка при обновлении профиля', 'error')
            
            return redirect(url_for('auth.profile'))
        
        elif form_type == 'password' and password_form.validate_on_submit():
            # Изменяем пароль
            result, status_code = AuthController.change_password({
                'current_password': password_form.current_password.data,
                'new_password': password_form.new_password.data,
                'new_password_confirm': password_form.new_password_confirm.data
            })
            
            if status_code == 200:
                flash(result.get('message', 'Пароль успешно изменен'), 'success')
            else:
                flash(result.get('error', 'Ошибка при изменении пароля'), 'error')
            
            return redirect(url_for('auth.profile'))
        
        else:
            # Ошибки валидации
            for form in [profile_form, password_form]:
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'{error}', 'error')
    
    return render_template('profile.html', 
                         profile_form=profile_form, 
                         password_form=password_form,
                         user=current_user)

# ========== API ENDPOINTS ==========

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint для входа в систему"""
    if current_user.is_authenticated:
        return jsonify({'error': 'Пользователь уже авторизован'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Данные не предоставлены'}), 400
    
    result, status_code = AuthController.login(data)
    return jsonify(result), status_code

@auth_bp.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint для регистрации"""
    if current_user.is_authenticated:
        return jsonify({'error': 'Пользователь уже авторизован'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Данные не предоставлены'}), 400
    
    result, status_code = AuthController.register(data)
    return jsonify(result), status_code

@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    """API endpoint для выхода из системы"""
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

@auth_bp.route('/api/forgot-password', methods=['POST'])
def api_forgot_password():
    """API endpoint для восстановления пароля"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Данные не предоставлены'}), 400
    
    result, status_code = AuthController.forgot_password(data)
    return jsonify(result), status_code

@auth_bp.route('/api/reset-password/<token>', methods=['POST'])
def api_reset_password(token):
    """API endpoint для сброса пароля"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Данные не предоставлены'}), 400
    
    result, status_code = AuthController.reset_password(token, data)
    return jsonify(result), status_code

@auth_bp.route('/api/change-password', methods=['POST'])
def api_change_password():
    """API endpoint для изменения пароля"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Необходима авторизация'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Данные не предоставлены'}), 400
    
    result, status_code = AuthController.change_password(data)
    return jsonify(result), status_code

@auth_bp.route('/api/verify-email/<token>', methods=['POST'])
def api_verify_email(token):
    """API endpoint для верификации email"""
    result, status_code = AuthController.verify_email(token)
    return jsonify(result), status_code

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

# Обработчик перед запросом для сохранения страницы перенаправления
@auth_bp.before_app_request
def before_request():
    """Сохраняем страницу, с которой пришел неавторизованный пользователь"""
    
    # Список страниц, требующих авторизации
    protected_endpoints = ['auth.profile', 'collections.create_collection', 'collections.edit_collection']
    
    if (request.endpoint in protected_endpoints and 
        not current_user.is_authenticated and 
        request.method == 'GET'):
        session['next_page'] = request.url

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