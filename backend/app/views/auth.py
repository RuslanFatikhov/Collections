from flask import Blueprint, request, redirect, url_for, render_template, flash, jsonify, session
from flask_login import current_user, login_required
from app.controllers.auth_controller import AuthController
from app.forms.auth import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm, ProfileForm, ChangePasswordForm

# Создание Blueprint для аутентификации
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа в систему"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            result, status_code = AuthController.login({
                'email': form.email.data,
                'password': form.password.data,
                'remember_me': form.remember_me.data
            })
            
            if status_code == 200:
                user_name = result['user'].get('name', 'Пользователь')
                flash(f'Добро пожаловать, {user_name}!', 'success')
                next_page = request.args.get('next') or url_for('index')
                return redirect(next_page)
            else:
                flash(result.get('error', 'Ошибка при входе'), 'error')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{error}', 'error')
    
    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegisterForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            result, status_code = AuthController.register({
                'name': form.name.data,
                'email': form.email.data,
                'password': form.password.data,
                'password_confirm': form.password_confirm.data
            })
            
            if status_code == 201:
                flash(result.get('message', 'Регистрация прошла успешно'), 'success')
                return redirect(url_for('auth.login'))
            else:
                flash(result.get('error', 'Ошибка при регистрации'), 'error')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{error}', 'error')
    
    return render_template('register.html', form=form)

@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    """Выход из системы"""
    try:
        result, status_code = AuthController.logout()
        
        if status_code == 200:
            flash('Вы успешно вышли из системы', 'info')
        else:
            flash('Ошибка при выходе из системы', 'error')
            
    except Exception as e:
        flash('Произошла ошибка при выходе', 'error')
    
    return redirect(url_for('index'))

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

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Страница восстановления пароля"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = ForgotPasswordForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            result, status_code = AuthController.forgot_password({
                'email': form.email.data
            })
            
            flash(result.get('message', 'Инструкция отправлена на email'), 'info')
            return redirect(url_for('auth.login'))
        else:
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
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{error}', 'error')
    
    return render_template('reset_password.html', form=form, token=token)
