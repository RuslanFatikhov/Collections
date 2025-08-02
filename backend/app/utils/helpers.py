import os
import uuid
import hashlib
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename
from flask import current_app
import mimetypes

class FileUploadError(Exception):
    """Кастомное исключение для ошибок загрузки файлов"""
    pass

# Разрешенные типы файлов
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 
    'image/gif', 'image/webp'
}

# Размеры изображений
IMAGE_SIZES = {
    'original': None,  # Оригинальный размер
    'medium': (800, 800),  # Средний размер 800x800 (сохраняя пропорции)
    'thumbnail': (200, 200)  # Миниатюра 200x200 (сохраняя пропорции)
}

# Максимальный размер файла (10MB в байтах)
MAX_FILE_SIZE = 10 * 1024 * 1024


def allowed_file(filename):
    """
    Проверяет, разрешен ли тип файла
    """
    if not filename:
        return False
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def validate_image_file(file):
    """
    Валидация загруженного изображения
    """
    # Проверка наличия файла
    if not file or not file.filename:
        raise FileUploadError("Файл не выбран")
    
    # Проверка расширения
    if not allowed_file(file.filename):
        raise FileUploadError("Недопустимый тип файла. Разрешены: JPG, PNG, GIF, WebP")
    
    # Проверка MIME-типа
    mime_type = file.content_type
    if mime_type not in ALLOWED_MIME_TYPES:
        raise FileUploadError("Недопустимый MIME-тип файла")
    
    # Проверка размера файла
    file.seek(0, 2)  # Переходим в конец файла
    file_size = file.tell()
    file.seek(0)  # Возвращаемся в начало
    
    if file_size > MAX_FILE_SIZE:
        raise FileUploadError(f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE // (1024*1024)}MB")
    
    if file_size == 0:
        raise FileUploadError("Файл пустой")
    
    return True


def validate_image_content(file):
    """
    Дополнительная валидация содержимого изображения с помощью PIL
    """
    try:
        file.seek(0)
        with Image.open(file) as img:
            # Проверяем, что это действительно изображение
            img.verify()
            
        # Возвращаем указатель в начало для дальнейшего использования
        file.seek(0)
        return True
        
    except Exception as e:
        raise FileUploadError("Файл поврежден или не является изображением")


def generate_unique_filename(original_filename):
    """
    Генерирует уникальное имя файла
    """
    # Извлекаем расширение
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    
    # Генерируем уникальный идентификатор
    unique_id = str(uuid.uuid4())
    
    # Создаем безопасное имя файла
    if ext:
        return f"{unique_id}.{ext}"
    else:
        return unique_id


def get_file_hash(file):
    """
    Вычисляет MD5 хеш файла для проверки дубликатов
    """
    file.seek(0)
    hash_md5 = hashlib.md5()
    
    for chunk in iter(lambda: file.read(4096), b""):
        hash_md5.update(chunk)
    
    file.seek(0)
    return hash_md5.hexdigest()


def create_upload_directories():
    """
    Создает необходимые директории для загрузки файлов
    """
    base_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    
    directories = [
        base_dir,
        os.path.join(base_dir, 'original'),
        os.path.join(base_dir, 'medium'),
        os.path.join(base_dir, 'thumbnail')
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)


def resize_image(image_path, output_path, size_tuple):
    """
    Изменяет размер изображения с сохранением пропорций
    """
    try:
        with Image.open(image_path) as img:
            # Конвертируем в RGB если это RGBA (для JPEG)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Создаем белый фон
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Изменяем размер с сохранением пропорций
            img.thumbnail(size_tuple, Image.Resampling.LANCZOS)
            
            # Применяем автоповорот на основе EXIF данных
            img = ImageOps.exif_transpose(img)
            
            # Сохраняем с оптимизацией
            img.save(output_path, optimize=True, quality=85)
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Ошибка при изменении размера изображения: {str(e)}")
        return False


def save_uploaded_image(file, filename):
    """
    Сохраняет загруженное изображение в разных размерах
    """
    try:
        create_upload_directories()
        
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Путь для оригинального файла
        original_path = os.path.join(upload_folder, 'original', filename)
        
        # Сохраняем оригинал
        file.save(original_path)
        
        # Создаем изображения разных размеров
        saved_sizes = {'original': filename}
        
        for size_name, size_tuple in IMAGE_SIZES.items():
            if size_name == 'original':
                continue
                
            size_folder = os.path.join(upload_folder, size_name)
            size_path = os.path.join(size_folder, filename)
            
            if resize_image(original_path, size_path, size_tuple):
                saved_sizes[size_name] = filename
            else:
                current_app.logger.warning(f"Не удалось создать изображение размера {size_name}")
        
        return saved_sizes
        
    except Exception as e:
        current_app.logger.error(f"Ошибка при сохранении изображения: {str(e)}")
        raise FileUploadError(f"Ошибка при сохранении файла: {str(e)}")


def delete_uploaded_image(filename):
    """
    Удаляет изображение во всех размерах
    """
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        deleted_files = []
        
        for size_name in IMAGE_SIZES.keys():
            file_path = os.path.join(upload_folder, size_name, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_files.append(f"{size_name}/{filename}")
        
        return deleted_files
        
    except Exception as e:
        current_app.logger.error(f"Ошибка при удалении изображения: {str(e)}")
        return []


def get_image_info(file):
    """
    Получает информацию об изображении
    """
    try:
        file.seek(0)
        with Image.open(file) as img:
            info = {
                'width': img.width,
                'height': img.height,
                'format': img.format,
                'mode': img.mode,
                'size_bytes': file.tell()
            }
        file.seek(0)
        return info
        
    except Exception:
        return None


def is_safe_path(path):
    """
    Проверяет безопасность пути файла (защита от path traversal)
    """
    # Получаем абсолютный путь и проверяем, что он находится в разрешенной директории
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        abs_upload_folder = os.path.abspath(upload_folder)
        abs_path = os.path.abspath(path)
        
        return abs_path.startswith(abs_upload_folder)
    except:
        return False


def format_file_size(size_bytes):
    """
    Форматирует размер файла в человекочитаемый вид
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"