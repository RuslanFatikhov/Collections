import os
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.exceptions import RequestEntityTooLarge
from ..models.user import User
from ..utils.helpers import (
    validate_image_file,
    validate_image_content,
    generate_unique_filename,
    get_image_info,
    format_file_size,
    FileUploadError
)


class ProfileController:
    """Контроллер для работы с профилем пользователя"""
    
    @staticmethod
    @login_required
    def get_profile():
        """
        Получение профиля текущего пользователя
        GET /api/profile
        
        Returns:
            JSON: Данные профиля пользователя
        """
        try:
            profile_data = {
                'success': True,
                'profile': {
                    **current_user.to_dict(),
                    'avatar_info': current_user.get_avatar_info(),
                    'collections_count': current_user.get_collections_count(),
                    'public_collections_count': len(current_user.get_public_collections())
                }
            }
            
            return jsonify(profile_data), 200
            
        except Exception as e:
            current_app.logger.error(f"Error getting profile for user {current_user.id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Ошибка при получении профиля'
            }), 500
    
    @staticmethod
    @login_required
    def update_profile():
        """
        Обновление профиля пользователя
        PUT /api/profile
        
        Expected JSON:
        {
            "name": "Новое имя"
        }
        
        Returns:
            JSON: Обновленные данные профиля
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Данные не переданы'
                }), 400
            
            # Валидация имени
            name = data.get('name', '').strip()
            if not name:
                return jsonify({
                    'success': False,
                    'error': 'Имя не может быть пустым'
                }), 400
            
            if len(name) > 100:
                return jsonify({
                    'success': False,
                    'error': 'Имя слишком длинное (максимум 100 символов)'
                }), 400
            
            # Обновляем профиль
            update_data = {
                'name': name
            }
            
            if current_user.update_profile(update_data):
                return jsonify({
                    'success': True,
                    'message': 'Профиль успешно обновлен',
                    'profile': current_user.to_dict()
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Ошибка при обновлении профиля'
                }), 500
                
        except Exception as e:
            current_app.logger.error(f"Error updating profile for user {current_user.id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Ошибка при обновлении профиля'
            }), 500
    
    @staticmethod
    @login_required
    def upload_avatar():
        """
        Загрузка аватара пользователя
        POST /api/profile/avatar
        
        Expects multipart/form-data with 'avatar' field
        
        Returns:
            JSON: Информация о загруженном аватаре
        """
        try:
            # Проверяем наличие файла в запросе
            if 'avatar' not in request.files:
                return jsonify({
                    'success': False,
                    'error': 'Файл аватара не найден в запросе'
                }), 400
            
            file = request.files['avatar']
            
            # Проверяем, что файл выбран
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'Файл не выбран'
                }), 400
            
            # Валидация файла
            validate_image_file(file)
            validate_image_content(file)
            
            # Получаем информацию об изображении
            image_info = get_image_info(file)
            if not image_info:
                return jsonify({
                    'success': False,
                    'error': 'Не удалось получить информацию об изображении'
                }), 400
            
            # Генерируем уникальное имя файла
            original_filename = file.filename
            unique_filename = generate_unique_filename(original_filename)
            
            # Сохраняем аватар в специальной папке
            saved_files = ProfileController._save_avatar_image(file, unique_filename)
            
            if saved_files:
                # Обновляем аватар пользователя
                if current_user.update_avatar(unique_filename):
                    current_app.logger.info(
                        f"Avatar uploaded successfully: {unique_filename} by user {current_user.id}"
                    )
                    
                    return jsonify({
                        'success': True,
                        'message': 'Аватар успешно загружен',
                        'avatar': {
                            'filename': unique_filename,
                            'original_filename': original_filename,
                            'size_bytes': image_info['size_bytes'],
                            'size_formatted': format_file_size(image_info['size_bytes']),
                            'width': image_info['width'],
                            'height': image_info['height'],
                            'format': image_info['format'],
                            'urls': {
                                'thumbnail': current_user.get_avatar_url('thumbnail'),
                                'medium': current_user.get_avatar_url('medium'),
                                'original': current_user.get_avatar_url('original')
                            }
                        }
                    }), 201
                else:
                    # Если не удалось обновить в БД, удаляем загруженные файлы
                    ProfileController._delete_avatar_files(unique_filename)
                    return jsonify({
                        'success': False,
                        'error': 'Ошибка при сохранении аватара в базе данных'
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': 'Ошибка при сохранении файла аватара'
                }), 500
                
        except FileUploadError as e:
            current_app.logger.warning(f"Avatar upload validation failed: {str(e)} by user {current_user.id}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
            
        except RequestEntityTooLarge:
            current_app.logger.warning(f"Avatar file too large uploaded by user {current_user.id}")
            return jsonify({
                'success': False,
                'error': 'Файл слишком большой'
            }), 413
            
        except Exception as e:
            current_app.logger.error(f"Unexpected error during avatar upload: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Внутренняя ошибка сервера'
            }), 500
    
    @staticmethod
    @login_required
    def delete_avatar():
        """
        Удаление аватара пользователя
        DELETE /api/profile/avatar
        
        Returns:
            JSON: Результат удаления аватара
        """
        try:
            if not current_user.has_avatar():
                return jsonify({
                    'success': False,
                    'error': 'У пользователя нет аватара'
                }), 400
            
            if current_user.delete_avatar():
                current_app.logger.info(f"Avatar deleted successfully by user {current_user.id}")
                return jsonify({
                    'success': True,
                    'message': 'Аватар успешно удален'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Ошибка при удалении аватара'
                }), 500
                
        except Exception as e:
            current_app.logger.error(f"Error deleting avatar for user {current_user.id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Ошибка при удалении аватара'
            }), 500
    
    @staticmethod
    def _save_avatar_image(file, filename):
        """
        Сохраняет аватар в специальной папке с разными размерами
        
        Args:
            file: Файл изображения
            filename (str): Имя файла
        
        Returns:
            dict: Информация о сохраненных размерах
        """
        try:
            from ..utils.helpers import resize_image, create_upload_directories
            
            # Создаем директории для аватаров
            ProfileController._create_avatar_directories()
            
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            
            # Путь для оригинального файла аватара
            original_path = os.path.join(upload_folder, 'avatars', 'original', filename)
            
            # Сохраняем оригинал
            file.save(original_path)
            
            # Размеры для аватаров
            avatar_sizes = {
                'medium': (400, 400),    # Основной размер для профиля
                'thumbnail': (100, 100)  # Маленький размер для списков
            }
            
            # Создаем изображения разных размеров
            saved_sizes = {'original': filename}
            
            for size_name, size_tuple in avatar_sizes.items():
                size_folder = os.path.join(upload_folder, 'avatars', size_name)
                size_path = os.path.join(size_folder, filename)
                
                if resize_image(original_path, size_path, size_tuple):
                    saved_sizes[size_name] = filename
                else:
                    current_app.logger.warning(f"Не удалось создать аватар размера {size_name}")
            
            return saved_sizes
            
        except Exception as e:
            current_app.logger.error(f"Ошибка при сохранении аватара: {str(e)}")
            return None
    
    @staticmethod
    def _create_avatar_directories():
        """Создает необходимые директории для аватаров"""
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        directories = [
            os.path.join(upload_folder, 'avatars'),
            os.path.join(upload_folder, 'avatars', 'original'),
            os.path.join(upload_folder, 'avatars', 'medium'),
            os.path.join(upload_folder, 'avatars', 'thumbnail')
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
    
    @staticmethod
    def _delete_avatar_files(filename):
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
        except Exception as e:
            current_app.logger.error(f"Error deleting avatar files for {filename}: {str(e)}")