from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
import re

class LoginForm(FlaskForm):
    """Форма авторизации"""
    email = StringField('Email', validators=[
        DataRequired(message='Email обязателен'),
        Email(message='Введите корректный email')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль обязателен')
    ])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class RegisterForm(FlaskForm):
    """Форма регистрации"""
    name = StringField('Имя', validators=[
        DataRequired(message='Имя обязательно'),
        Length(min=2, max=100, message='Имя должно быть от 2 до 100 символов')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email обязателен'),
        Email(message='Введите корректный email'),
        Length(max=120, message='Email не должен превышать 120 символов')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль обязателен'),
        Length(min=6, max=128, message='Пароль должен быть от 6 до 128 символов')
    ])
    password_confirm = PasswordField('Подтвердите пароль', validators=[
        DataRequired(message='Подтверждение пароля обязательно'),
        EqualTo('password', message='Пароли не совпадают')
    ])
    submit = SubmitField('Зарегистрироваться')

    def validate_email(self, email):
        """Проверка уникальности email"""
        from app.models.user import User
        user = User.find_by_email(email.data.lower())
        if user:
            raise ValidationError('Пользователь с таким email уже существует')

    def validate_password(self, password):
        """Проверка сложности пароля"""
        password_value = password.data
        
        if not re.search(r'\d', password_value):
            raise ValidationError('Пароль должен содержать хотя бы одну цифру')
        
        if not re.search(r'[a-zA-Zа-яА-Я]', password_value):
            raise ValidationError('Пароль должен содержать хотя бы одну букву')

class ForgotPasswordForm(FlaskForm):
    """Форма восстановления пароля"""
    email = StringField('Email', validators=[
        DataRequired(message='Email обязателен'),
        Email(message='Введите корректный email')
    ])
    submit = SubmitField('Восстановить пароль')

class ResetPasswordForm(FlaskForm):
    """Форма сброса пароля"""
    password = PasswordField('Новый пароль', validators=[
        DataRequired(message='Пароль обязателен'),
        Length(min=6, max=128, message='Пароль должен быть от 6 до 128 символов')
    ])
    password_confirm = PasswordField('Подтвердите новый пароль', validators=[
        DataRequired(message='Подтверждение пароля обязательно'),
        EqualTo('password', message='Пароли не совпадают')
    ])
    submit = SubmitField('Изменить пароль')

class ChangePasswordForm(FlaskForm):
    """Форма изменения пароля в профиле"""
    current_password = PasswordField('Текущий пароль', validators=[
        DataRequired(message='Введите текущий пароль')
    ])
    new_password = PasswordField('Новый пароль', validators=[
        DataRequired(message='Новый пароль обязателен'),
        Length(min=6, max=128, message='Пароль должен быть от 6 до 128 символов')
    ])
    new_password_confirm = PasswordField('Подтвердите новый пароль', validators=[
        DataRequired(message='Подтверждение пароля обязательно'),
        EqualTo('new_password', message='Пароли не совпадают')
    ])
    submit = SubmitField('Изменить пароль')

    def __init__(self, user, *args, **kwargs):
        super(ChangePasswordForm, self).__init__(*args, **kwargs)
        self.user = user

    def validate_current_password(self, current_password):
        """Проверка текущего пароля"""
        if not self.user.check_password(current_password.data):
            raise ValidationError('Неверный текущий пароль')

class ProfileForm(FlaskForm):
    """Форма редактирования профиля"""
    name = StringField('Имя', validators=[
        DataRequired(message='Имя обязательно'),
        Length(min=2, max=100, message='Имя должно быть от 2 до 100 символов')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email обязателен'),
        Email(message='Введите корректный email'),
        Length(max=120, message='Email не должен превышать 120 символов')
    ])
    submit = SubmitField('Сохранить изменения')

    def __init__(self, user, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.user = user

    def validate_email(self, email):
        """Проверка уникальности email (если изменился)"""
        if email.data.lower() != self.user.email.lower():
            from app.models.user import User
            user = User.find_by_email(email.data.lower())
            if user:
                raise ValidationError('Пользователь с таким email уже существует')
