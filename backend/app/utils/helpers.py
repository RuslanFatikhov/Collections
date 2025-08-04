import os
import uuid
import hashlib
import secrets
from flask import current_app

class FileUploadError(Exception):
    """Кастомное исключение для ошибок загрузки файлов"""
    pass

def generate_random_token(length=32):
    """Генерирует криптографически стойкий случайный токен"""
    return secrets.token_urlsafe(length)

def send_email(to_email, subject, body, html_body=None):
    """Отправляет email сообщение"""
    try:
        from flask_mail import Message
        from app import mail
        
        msg = Message(
            subject=subject,
            recipients=[to_email],
            body=body,
            html=html_body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        
        if current_app.config.get('MAIL_SUPPRESS_SEND'):
            print(f"EMAIL SUPPRESSED: To: {to_email}, Subject: {subject}")
            return True
        
        mail.send(msg)
        return True
        
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

def validate_image_content(file):
    """Дополнительная валидация содержимого изображения с помощью PIL"""
    try:
        from PIL import Image
        file.seek(0)
        with Image.open(file) as img:
            img.verify()
        file.seek(0)
        return True
    except Exception as e:
        raise FileUploadError("Файл поврежден или не является изображением")

validate_image_file = validate_image_content

def generate_unique_filename(original_filename):
    """Генерирует уникальное имя файла"""
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_id = str(uuid.uuid4())
    return f"{unique_id}.{ext}" if ext else unique_id

def save_uploaded_image(file, filename):
    """Сохраняет загруженное изображение в разных размерах"""
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        os.makedirs(os.path.join(upload_folder, 'original'), exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'medium'), exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'thumbnail'), exist_ok=True)
        
        original_path = os.path.join(upload_folder, 'original', filename)
        file.save(original_path)
        
        return {'original': filename}
        
    except Exception as e:
        current_app.logger.error(f"Ошибка при сохранении изображения: {str(e)}")
        raise FileUploadError(f"Ошибка при сохранении файла: {str(e)}")

def delete_uploaded_image(filename):
    """Удаляет изображение во всех размерах"""
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        deleted_files = []
        
        for size_name in ['original', 'medium', 'thumbnail']:
            file_path = os.path.join(upload_folder, size_name, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_files.append(f"{size_name}/{filename}")
        
        return deleted_files
        
    except Exception as e:
        current_app.logger.error(f"Ошибка при удалении изображения: {str(e)}")
        return []

def get_image_info(file):
    """Получает информацию об изображении"""
    try:
        from PIL import Image
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

def get_file_hash(file):
    """Вычисляет MD5 хеш файла для проверки дубликатов"""
    file.seek(0)
    hash_md5 = hashlib.md5()
    
    for chunk in iter(lambda: file.read(4096), b""):
        hash_md5.update(chunk)
    
    file.seek(0)
    return hash_md5.hexdigest()

def is_safe_path(path):
    """Проверяет безопасность пути файла (защита от path traversal)"""
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        abs_upload_folder = os.path.abspath(upload_folder)
        abs_path = os.path.abspath(path)
        
        return abs_path.startswith(abs_upload_folder)
    except:
        return False

def format_file_size(size_bytes):
    """Форматирует размер файла в человекочитаемый вид"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"

def resize_image(image_path, output_path, size_tuple):
    """Изменяет размер изображения с сохранением пропорций"""
    try:
        from PIL import Image, ImageOps
        
        with Image.open(image_path) as img:
            # Конвертируем в RGB если это RGBA (для JPEG)
            if img.mode in ('RGBA', 'LA', 'P'):
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
