from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import os
from flask import current_app

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)
    blocked_at = db.Column(db.DateTime, nullable=True)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verification_token = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    collections = db.relationship('Collection', back_populates='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.name} ({self.email})>'
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user object to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'avatar_url': self.get_avatar_url(),
            'is_admin': self.is_admin,
            'is_blocked': self.is_blocked,
            'email_verified': self.email_verified,
            'blocked_at': self.blocked_at.isoformat() if self.blocked_at else None,
            'collections_count': self.get_collections_count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_public_dict(self):
        """Convert user object to public dictionary (for sharing)"""
        return {
            'id': self.id,
            'name': self.name,
            'avatar_url': self.get_avatar_url()
        }
    
    @staticmethod
    def find_by_email(email):
        """Find user by email"""
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def create_user(name, email, password):
        """Create new user with email and password"""
        user = User(name=name, email=email)
        user.set_password(password)
        return user
    
    def get_public_collections(self):
        """Get all public collections for this user"""
        return [collection for collection in self.collections if collection.is_public]
    
    def get_collections_count(self):
        """Get total number of collections for this user"""
        return len(self.collections)
    
    def verify_email(self):
        """Mark email as verified"""
        self.email_verified = True
        self.email_verification_token = None
        self.updated_at = datetime.utcnow()
    
    def is_email_verified(self):
        """Check if email is verified"""
        return self.email_verified
    
    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С АВАТАРОМ ==========
    
    def get_avatar_url(self, size='medium'):
        """
        Получить URL аватара пользователя
        
        Args:
            size (str): Размер аватара ('thumbnail', 'medium', 'original')
        
        Returns:
            str: URL аватара или None если аватар не установлен
        """
        if not self.avatar_url:
            return None
        
        # Если аватар - внешняя ссылка, возвращаем как есть
        if self.avatar_url.startswith(('http://', 'https://')):
            return self.avatar_url
        
        # Если аватар - локальный файл, формируем URL
        return f"/api/files/avatars/{size}/{self.avatar_url}"
    
    def update_avatar(self, filename):
        """
        Обновить аватар пользователя
        
        Args:
            filename (str): Имя файла аватара
        
        Returns:
            bool: True если успешно обновлен
        """
        try:
            # Удаляем старый аватар если он локальный
            self.delete_avatar()
            
            # Устанавливаем новый аватар
            self.avatar_url = filename
            self.updated_at = datetime.utcnow()
            db.session.commit()
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error updating avatar for user {self.id}: {str(e)}")
            db.session.rollback()
            return False
    
    def delete_avatar(self):
        """
        Удалить аватар пользователя
        
        Returns:
            bool: True если успешно удален
        """
        try:
            old_avatar = self.avatar_url
            
            # Удаляем файлы только если это локальный аватар
            if old_avatar and not old_avatar.startswith(('http://', 'https://')):
                self._delete_avatar_files(old_avatar)
            
            # Очищаем поле аватара
            self.avatar_url = None
            self.updated_at = datetime.utcnow()
            db.session.commit()
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error deleting avatar for user {self.id}: {str(e)}")
            db.session.rollback()
            return False
    
    def _delete_avatar_files(self, filename):
        """
        Удалить файлы аватара с диска
        
        Args:
            filename (str): Имя файла для удаления
        """
        try:
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            avatar_sizes = ['original', 'medium', 'thumbnail']
            
            for size in avatar_sizes:
                file_path = os.path.join(upload_folder, 'avatars', size, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    current_app.logger.info(f"Deleted avatar file: {file_path}")
        except Exception as e:
            current_app.logger.error(f"Error deleting avatar files for {filename}: {str(e)}")
    
    def has_avatar(self):
        """
        Проверить, есть ли у пользователя аватар
        
        Returns:
            bool: True если аватар установлен
        """
        return bool(self.avatar_url)
    
    def get_avatar_info(self):
        """
        Получить информацию об аватаре
        
        Returns:
            dict: Информация об аватаре
        """
        if not self.avatar_url:
            return {
                'has_avatar': False,
                'avatar_url': None,
                'is_external': False
            }
        
        is_external = self.avatar_url.startswith(('http://', 'https://'))
        
        return {
            'has_avatar': True,
            'avatar_url': self.get_avatar_url(),
            'is_external': is_external,
            'urls': {
                'thumbnail': self.get_avatar_url('thumbnail'),
                'medium': self.get_avatar_url('medium'),
                'original': self.get_avatar_url('original')
            } if not is_external else None
        }
    
    def update_profile(self, data):
        """
        Обновить профиль пользователя
        
        Args:
            data (dict): Данные для обновления
        
        Returns:
            bool: True если успешно обновлен
        """
        try:
            # Обновляем разрешенные поля
            if 'name' in data and data['name'].strip():
                self.name = data['name'].strip()
            
            # Email можно обновлять, но нужно повторно верифицировать
            if 'email' in data and data['email'].strip() and data['email'] != self.email:
                self.email = data['email'].strip()
                self.email_verified = False  # Требуем повторную верификацию
            
            # Обновление пароля
            if 'password' in data and data['password']:
                self.set_password(data['password'])
            
            self.updated_at = datetime.utcnow()
            db.session.commit()
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error updating profile for user {self.id}: {str(e)}")
            db.session.rollback()
            return False