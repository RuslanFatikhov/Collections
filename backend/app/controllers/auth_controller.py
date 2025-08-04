from datetime import datetime, timedelta
from flask import session, current_app, url_for, request
from flask_login import login_user, logout_user, current_user
from app import db
from app.models.user import User
from app.forms.auth import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm, ChangePasswordForm
from app.utils.helpers import generate_random_token, send_email
import secrets

class AuthController:
    """Контроллер для обработки аутентификации через email/password"""
    
    @staticmethod
    def login(form_data):
        """Авторизация пользователя"""
        try:
            form = LoginForm(data=form_data)
            
            if not form.validate():
                return {'error': 'Проверьте правильность заполнения формы', 'errors': form.errors}, 400
            
            # Ищем пользователя по email
            user = User.find_by_email(form.email.data.lower())
            
            if not user:
                current_app.logger.warning(f'Login attempt with non-existent email: {form.email.data}')
                return {'error': 'Неверный email или пароль'}, 401
            
            # Проверяем пароль
            if not user.check_password(form.password.data):
                current_app.logger.warning(f'Failed login attempt for user: {user.email}')
                return {'error': 'Неверный email или пароль'}, 401
            
            # Проверяем, не заблокирован ли пользователь
            if user.is_blocked:
                current_app.logger.warning(f'Blocked user login attempt: {user.email}')
                return {'error': 'Ваш аккаунт заблокирован. Обратитесь к администратору'}, 403
            
            # Авторизуем пользователя
            remember = form.remember_me.data
            login_user(user, remember=remember)
            
            current_app.logger.info(f'User {user.email} successfully logged in')
            
            return {
                'success': True, 
                'user': user.to_dict(),
                'message': 'Вход выполнен успешно'
            }, 200
            
        except Exception as e:
            current_app.logger.error(f'Error during login: {str(e)}')
            return {'error': 'Ошибка при входе в систему'}, 500
    
    @staticmethod
    def register(form_data):
        """Регистрация нового пользователя"""
        try:
            form = RegisterForm(data=form_data)
            
            if not form.validate():
                return {'error': 'Проверьте правильность заполнения формы', 'errors': form.errors}, 400
            
            # Создаем нового пользователя
            user = User.create_user(
                name=form.name.data.strip(),
                email=form.email.data.lower().strip(),
                password=form.password.data
            )
            
            # Генерируем токен для верификации email
            user.email_verification_token = generate_random_token()
            
            # Сохраняем пользователя
            db.session.add(user)
            db.session.commit()
            
            # Отправляем email для верификации
            AuthController._send_verification_email(user)
            
            current_app.logger.info(f'New user registered: {user.email}')
            
            return {
                'success': True, 
                'message': 'Регистрация прошла успешно. Проверьте email для подтверждения аккаунта',
                'user_id': user.id
            }, 201
            
        except Exception as e:
            current_app.logger.error(f'Error during registration: {str(e)}')
            db.session.rollback()
            return {'error': 'Ошибка при регистрации'}, 500
    
    @staticmethod
    def verify_email(token):
        """Верификация email по токену"""
        try:
            if not token:
                return {'error': 'Токен не предоставлен'}, 400
            
            # Ищем пользователя по токену
            user = User.query.filter_by(email_verification_token=token).first()
            
            if not user:
                return {'error': 'Неверный или устаревший токен'}, 400
            
            # Проверяем, не верифицирован ли уже email
            if user.email_verified:
                return {'error': 'Email уже подтвержден'}, 400
            
            # Верифицируем email
            user.verify_email()
            db.session.commit()
            
            current_app.logger.info(f'Email verified for user: {user.email}')
            
            return {
                'success': True, 
                'message': 'Email успешно подтвержден'
            }, 200
            
        except Exception as e:
            current_app.logger.error(f'Error during email verification: {str(e)}')
            db.session.rollback()
            return {'error': 'Ошибка при верификации email'}, 500
    
    @staticmethod
    def forgot_password(form_data):
        """Запрос на восстановление пароля"""
        try:
            form = ForgotPasswordForm(data=form_data)
            
            if not form.validate():
                return {'error': 'Проверьте правильность заполнения формы', 'errors': form.errors}, 400
            
            user = User.find_by_email(form.email.data.lower())
            
            if user:
                # Генерируем токен для сброса пароля
                reset_token = generate_random_token()
                
                # Сохраняем токен в сессии (или можно в БД добавить поле)
                session[f'password_reset_token_{user.id}'] = {
                    'token': reset_token,
                    'expires': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                    'user_id': user.id
                }
                
                # Отправляем email с инструкцией
                AuthController._send_password_reset_email(user, reset_token)
                
                current_app.logger.info(f'Password reset requested for user: {user.email}')
            
            # Всегда возвращаем успех для безопасности (не раскрываем существование email)
            return {
                'success': True, 
                'message': 'Если такой email существует, на него будет отправлена инструкция по восстановлению пароля'
            }, 200
            
        except Exception as e:
            current_app.logger.error(f'Error during forgot password: {str(e)}')
            return {'error': 'Ошибка при запросе восстановления пароля'}, 500
    
    @staticmethod
    def reset_password(token, form_data):
        """Сброс пароля по токену"""
        try:
            if not token:
                return {'error': 'Токен не предоставлен'}, 400
            
            # Ищем токен в сессии
            reset_data = None
            user_id = None
            
            for key, value in session.items():
                if key.startswith('password_reset_token_') and value.get('token') == token:
                    # Проверяем срок действия токена
                    expires = datetime.fromisoformat(value['expires'])
                    if datetime.utcnow() > expires:
                        session.pop(key, None)
                        return {'error': 'Токен истек'}, 400
                    
                    reset_data = value
                    user_id = value['user_id']
                    break
            
            if not reset_data:
                return {'error': 'Неверный или устаревший токен'}, 400
            
            # Валидируем форму
            form = ResetPasswordForm(data=form_data)
            if not form.validate():
                return {'error': 'Проверьте правильность заполнения формы', 'errors': form.errors}, 400
            
            # Находим пользователя
            user = User.query.get(user_id)
            if not user:
                return {'error': 'Пользователь не найден'}, 400
            
            # Обновляем пароль
            user.set_password(form.password.data)
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Удаляем токен из сессии
            for key in list(session.keys()):
                if key.startswith('password_reset_token_') and session[key].get('user_id') == user_id:
                    session.pop(key, None)
            
            current_app.logger.info(f'Password reset completed for user: {user.email}')
            
            return {
                'success': True, 
                'message': 'Пароль успешно изменен'
            }, 200
            
        except Exception as e:
            current_app.logger.error(f'Error during password reset: {str(e)}')
            db.session.rollback()
            return {'error': 'Ошибка при сбросе пароля'}, 500
    
    @staticmethod
    def change_password(form_data):
        """Изменение пароля в профиле"""
        try:
            if not current_user.is_authenticated:
                return {'error': 'Необходима авторизация'}, 401
            
            form = ChangePasswordForm(current_user, data=form_data)
            
            if not form.validate():
                return {'error': 'Проверьте правильность заполнения формы', 'errors': form.errors}, 400
            
            # Обновляем пароль
            current_user.set_password(form.new_password.data)
            current_user.updated_at = datetime.utcnow()
            db.session.commit()
            
            current_app.logger.info(f'Password changed for user: {current_user.email}')
            
            return {
                'success': True, 
                'message': 'Пароль успешно изменен'
            }, 200
            
        except Exception as e:
            current_app.logger.error(f'Error during password change: {str(e)}')
            db.session.rollback()
            return {'error': 'Ошибка при изменении пароля'}, 500
    
    @staticmethod
    def logout():
        """Выход пользователя из системы"""
        try:
            user_email = current_user.email if current_user.is_authenticated else None
            
            # Выходим из системы
            logout_user()
            
            # Очищаем сессию
            session.clear()
            
            current_app.logger.info(f'User {user_email} logged out')
            
            return {
                'success': True, 
                'message': 'Вы успешно вышли из системы'
            }, 200
            
        except Exception as e:
            current_app.logger.error(f'Error during logout: {str(e)}')
            return {'error': 'Ошибка при выходе'}, 500
    
    @staticmethod
    def get_current_user():
        """Получение информации о текущем пользователе"""
        try:
            if not current_user.is_authenticated:
                return {'error': 'Пользователь не авторизован'}, 401
            
            return {
                'success': True,
                'user': current_user.to_dict()
            }, 200
            
        except Exception as e:
            current_app.logger.error(f'Error getting current user: {str(e)}')
            return {'error': 'Ошибка получения данных пользователя'}, 500
    
    @staticmethod
    def _send_verification_email(user):
        """Отправка email для верификации"""
        try:
            verification_url = url_for(
                'auth.verify_email', 
                token=user.email_verification_token, 
                _external=True
            )
            
            subject = 'Подтверждение регистрации - Collections'
            body = f"""
            Здравствуйте, {user.name}!
            
            Для завершения регистрации в Collections перейдите по ссылке:
            {verification_url}
            
            Если вы не регистрировались на нашем сайте, просто проигнорируйте это письмо.
            
            С уважением,
            Команда Collections
            """
            
            send_email(user.email, subject, body)
            
        except Exception as e:
            current_app.logger.error(f'Error sending verification email to {user.email}: {str(e)}')
    
    @staticmethod
    def _send_password_reset_email(user, reset_token):
        """Отправка email для сброса пароля"""
        try:
            reset_url = url_for(
                'auth.reset_password_form', 
                token=reset_token, 
                _external=True
            )
            
            subject = 'Восстановление пароля - Collections'
            body = f"""
            Здравствуйте, {user.name}!
            
            Вы запросили восстановление пароля. Для создания нового пароля перейдите по ссылке:
            {reset_url}
            
            Ссылка действительна в течение 1 часа.
            
            Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.
            
            С уважением,
            Команда Collections
            """
            
            send_email(user.email, subject, body)
            
        except Exception as e:
            current_app.logger.error(f'Error sending password reset email to {user.email}: {str(e)}')