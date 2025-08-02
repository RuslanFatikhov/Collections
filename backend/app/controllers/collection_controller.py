from flask import jsonify, request, current_app
from flask_login import current_user, login_required
from app.models.collection import Collection
from app.models.item import Item
from app.models.audit_log import AuditAction, ResourceType
from app import db
from app.utils.logger import AuditLogger
from app.utils.security import SecurityValidator, validate_json_input, sanitize_html
from app.utils.rate_limiter import api_read_rate_limit, api_write_rate_limit, api_delete_rate_limit
import json


class CollectionController:
    
    @staticmethod
    @login_required
    @api_write_rate_limit()
    @validate_json_input(
        required_fields={
            'name': SecurityValidator.validate_collection_name
        },
        optional_fields={
            'description': lambda x: SecurityValidator.validate_text(x, 0, SecurityValidator.MAX_DESCRIPTION_LENGTH, "Description"),
            'custom_fields': SecurityValidator.validate_custom_fields,
            'cover_image': lambda x: (True, "Valid") if isinstance(x, str) else (False, "Cover image must be a string"),
            'is_public': lambda x: (True, "Valid") if isinstance(x, bool) else (False, "is_public must be a boolean")
        }
    )
    def create_collection():
        """Создание новой коллекции"""
        try:
            data = request.get_json()
            
            # Дополнительная очистка данных
            name = sanitize_html(data.get('name', '').strip())
            description = sanitize_html(data.get('description', '').strip())
            
            # Проверяем лимиты пользователя (например, максимум 100 коллекций)
            user_collections_count = Collection.query.filter_by(user_id=current_user.id).count()
            if user_collections_count >= 100:
                AuditLogger.log_action(
                    action=AuditAction.COLLECTION_CREATE,
                    resource_type=ResourceType.COLLECTION,
                    details={'error': 'collection_limit_exceeded', 'current_count': user_collections_count}
                )
                return jsonify({'error': 'Maximum number of collections reached (100)'}), 400
            
            # Проверяем уникальность названия коллекции для пользователя
            existing_collection = Collection.query.filter_by(
                user_id=current_user.id, 
                name=name
            ).first()
            
            if existing_collection:
                return jsonify({'error': 'Collection with this name already exists'}), 400
            
            # Создаем новую коллекцию
            collection = Collection(
                name=name,
                description=description,
                cover_image=data.get('cover_image'),
                custom_fields=json.dumps(data.get('custom_fields', [])),
                is_public=data.get('is_public', False),
                user_id=current_user.id
            )
            
            db.session.add(collection)
            db.session.commit()
            
            # Логируем создание коллекции
            AuditLogger.log_collection_action(
                action=AuditAction.COLLECTION_CREATE,
                collection_id=collection.id,
                collection_name=collection.name,
                user_id=current_user.id
            )
            
            current_app.logger.info(f'User {current_user.id} created collection "{collection.name}" (ID: {collection.id})')
            
            return jsonify({
                'message': 'Collection created successfully',
                'collection': collection.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error creating collection: {str(e)}')
            AuditLogger.log_action(
                action=AuditAction.COLLECTION_CREATE,
                resource_type=ResourceType.COLLECTION,
                details={'error': 'system_error', 'message': str(e)}
            )
            return jsonify({'error': 'Failed to create collection'}), 500
    
    @staticmethod
    @login_required
    @api_read_rate_limit()
    def get_user_collections():
        """Получение всех коллекций текущего пользователя"""
        try:
            # Получаем параметры пагинации
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)  # Максимум 100 на страницу
            
            # Получаем коллекции с пагинацией
            collections_query = Collection.query.filter_by(user_id=current_user.id)
            
            # Сортировка
            sort_by = request.args.get('sort', 'created_at')
            if sort_by == 'name':
                collections_query = collections_query.order_by(Collection.name)
            elif sort_by == 'updated_at':
                collections_query = collections_query.order_by(Collection.updated_at.desc())
            else:  # По умолчанию по дате создания
                collections_query = collections_query.order_by(Collection.created_at.desc())
            
            pagination = collections_query.paginate(
                page=page, 
                per_page=per_page, 
                error_out=False
            )
            
            collections = pagination.items
            
            # Логируем просмотр списка коллекций
            AuditLogger.log_action(
                action=AuditAction.COLLECTION_VIEW,
                resource_type=ResourceType.COLLECTION,
                details={'action': 'list_user_collections', 'count': len(collections)}
            )
            
            return jsonify({
                'collections': [collection.to_dict() for collection in collections],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }), 200
            
        except Exception as e:
            current_app.logger.error(f'Error getting user collections: {str(e)}')
            return jsonify({'error': 'Failed to retrieve collections'}), 500
    
    @staticmethod
    @api_read_rate_limit()
    def get_collection_by_id(collection_id):
        """Получение конкретной коллекции по ID"""
        try:
            # Валидируем ID коллекции
            try:
                collection_id = int(collection_id)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid collection ID'}), 400
            
            collection = Collection.query.get(collection_id)
            
            if not collection:
                # Логируем попытку доступа к несуществующей коллекции
                AuditLogger.log_action(
                    action=AuditAction.COLLECTION_VIEW,
                    resource_type=ResourceType.COLLECTION,
                    resource_id=collection_id,
                    details={'error': 'collection_not_found'}
                )
                return jsonify({'error': 'Collection not found'}), 404
            
            # Проверяем права доступа (только владелец может видеть приватные коллекции)
            if not collection.is_public and (not current_user.is_authenticated or collection.user_id != current_user.id):
                AuditLogger.log_action(
                    action=AuditAction.COLLECTION_VIEW,
                    resource_type=ResourceType.COLLECTION,
                    resource_id=collection_id,
                    details={'error': 'access_denied', 'is_public': collection.is_public}
                )
                return jsonify({'error': 'Access denied'}), 403
            
            # Логируем успешный просмотр коллекции
            AuditLogger.log_collection_action(
                action=AuditAction.COLLECTION_VIEW,
                collection_id=collection.id,
                collection_name=collection.name,
                user_id=current_user.id if current_user.is_authenticated else None
            )
            
            return jsonify({
                'collection': collection.to_dict()
            }), 200
            
        except Exception as e:
            current_app.logger.error(f'Error getting collection {collection_id}: {str(e)}')
            return jsonify({'error': 'Failed to retrieve collection'}), 500
    
    @staticmethod
    @login_required
    @api_write_rate_limit()
    @validate_json_input(
        optional_fields={
            'name': SecurityValidator.validate_collection_name,
            'description': lambda x: SecurityValidator.validate_text(x, 0, SecurityValidator.MAX_DESCRIPTION_LENGTH, "Description"),
            'custom_fields': SecurityValidator.validate_custom_fields,
            'cover_image': lambda x: (True, "Valid") if isinstance(x, str) else (False, "Cover image must be a string"),
            'is_public': lambda x: (True, "Valid") if isinstance(x, bool) else (False, "is_public must be a boolean")
        }
    )
    def update_collection(collection_id):
        """Обновление коллекции"""
        try:
            # Валидируем ID коллекции
            try:
                collection_id = int(collection_id)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid collection ID'}), 400
            
            collection = Collection.query.get(collection_id)
            
            if not collection:
                return jsonify({'error': 'Collection not found'}), 404
            
            # Проверяем права доступа (только владелец может редактировать)
            if collection.user_id != current_user.id:
                AuditLogger.log_action(
                    action=AuditAction.COLLECTION_UPDATE,
                    resource_type=ResourceType.COLLECTION,
                    resource_id=collection_id,
                    details={'error': 'access_denied'}
                )
                return jsonify({'error': 'Access denied'}), 403
            
            data = request.get_json()
            old_values = {}
            changes = {}
            
            # Обновляем поля
            if 'name' in data:
                new_name = sanitize_html(data['name'].strip())
                
                # Проверяем уникальность нового названия
                if new_name != collection.name:
                    existing_collection = Collection.query.filter_by(
                        user_id=current_user.id, 
                        name=new_name
                    ).first()
                    
                    if existing_collection:
                        return jsonify({'error': 'Collection with this name already exists'}), 400
                
                old_values['name'] = collection.name
                collection.name = new_name
                changes['name'] = new_name
            
            if 'description' in data:
                old_values['description'] = collection.description
                collection.description = sanitize_html(data['description'])
                changes['description'] = collection.description
            
            if 'cover_image' in data:
                old_values['cover_image'] = collection.cover_image
                collection.cover_image = data['cover_image']
                changes['cover_image'] = data['cover_image']
            
            if 'custom_fields' in data:
                old_values['custom_fields'] = collection.custom_fields
                collection.custom_fields = json.dumps(data['custom_fields'])
                changes['custom_fields'] = data['custom_fields']
            
            if 'is_public' in data:
                old_values['is_public'] = collection.is_public
                collection.is_public = data['is_public']
                changes['is_public'] = data['is_public']
            
            # Обновляем timestamp
            collection.updated_at = db.func.now()
            
            db.session.commit()
            
            # Логируем обновление коллекции
            AuditLogger.log_collection_action(
                action=AuditAction.COLLECTION_UPDATE,
                collection_id=collection.id,
                collection_name=collection.name,
                user_id=current_user.id
            )
            
            current_app.logger.info(f'User {current_user.id} updated collection {collection.id}')
            
            return jsonify({
                'message': 'Collection updated successfully',
                'collection': collection.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error updating collection {collection_id}: {str(e)}')
            AuditLogger.log_action(
                action=AuditAction.COLLECTION_UPDATE,
                resource_type=ResourceType.COLLECTION,
                resource_id=collection_id,
                details={'error': 'system_error', 'message': str(e)}
            )
            return jsonify({'error': 'Failed to update collection'}), 500
    
    @staticmethod
    @login_required
    @api_delete_rate_limit()
    def delete_collection(collection_id):
        """Удаление коллекции"""
        try:
            # Валидируем ID коллекции
            try:
                collection_id = int(collection_id)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid collection ID'}), 400
            
            collection = Collection.query.get(collection_id)
            
            if not collection:
                return jsonify({'error': 'Collection not found'}), 404
            
            # Проверяем права доступа (только владелец может удалять)
            if collection.user_id != current_user.id:
                AuditLogger.log_action(
                    action=AuditAction.COLLECTION_DELETE,
                    resource_type=ResourceType.COLLECTION,
                    resource_id=collection_id,
                    details={'error': 'access_denied'}
                )
                return jsonify({'error': 'Access denied'}), 403
            
            # Сохраняем информацию о коллекции для логирования
            collection_name = collection.name
            items_count = Item.query.filter_by(collection_id=collection_id).count()
            
            # Удаляем коллекцию (каскадное удаление предметов настроено в модели)
            db.session.delete(collection)
            db.session.commit()
            
            # Логируем удаление коллекции
            AuditLogger.log_action(
                action=AuditAction.COLLECTION_DELETE,
                resource_type=ResourceType.COLLECTION,
                resource_id=collection_id,
                user_id=current_user.id,
                details={
                    'collection_name': collection_name,
                    'items_deleted': items_count
                }
            )
            
            current_app.logger.info(f'User {current_user.id} deleted collection "{collection_name}" (ID: {collection_id}) with {items_count} items')
            
            return jsonify({
                'message': 'Collection deleted successfully'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error deleting collection {collection_id}: {str(e)}')
            AuditLogger.log_action(
                action=AuditAction.COLLECTION_DELETE,
                resource_type=ResourceType.COLLECTION,
                resource_id=collection_id,
                details={'error': 'system_error', 'message': str(e)}
            )
            return jsonify({'error': 'Failed to delete collection'}), 500

    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С ПРЕДМЕТАМИ ==========

    @staticmethod
    @login_required
    @api_write_rate_limit()
    @validate_json_input(
        optional_fields={
            'custom_data': lambda x: (True, "Valid") if isinstance(x, dict) else (False, "custom_data must be an object"),
            'images': lambda x: (True, "Valid") if isinstance(x, list) else (False, "images must be an array")
        }
    )
    def add_item_to_collection(collection_id):
        """Добавление нового предмета в коллекцию"""
        try:
            # Валидируем ID коллекции
            try:
                collection_id = int(collection_id)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid collection ID'}), 400
            
            # Получаем коллекцию
            collection = Collection.query.get(collection_id)
            
            if not collection:
                return jsonify({'error': 'Collection not found'}), 404
            
            # Проверяем права доступа (только владелец может добавлять предметы)
            if collection.user_id != current_user.id:
                AuditLogger.log_action(
                    action=AuditAction.ITEM_CREATE,
                    resource_type=ResourceType.ITEM,
                    details={'error': 'access_denied', 'collection_id': collection_id}
                )
                return jsonify({'error': 'Access denied'}), 403
            
            data = request.get_json()
            
            # Проверяем лимиты на количество предметов в коллекции
            items_count = Item.query.filter_by(collection_id=collection_id).count()
            if items_count >= 10000:  # Максимум 10000 предметов в коллекции
                return jsonify({'error': 'Maximum number of items in collection reached (10000)'}), 400
            
            # Валидируем данные согласно кастомным полям коллекции
            custom_data = data.get('custom_data', {})
            validation_result = CollectionController._validate_item_data(
                custom_data, 
                collection.get_custom_fields()
            )
            
            if not validation_result['valid']:
                return jsonify({'error': validation_result['error']}), 400
            
            # Очищаем текстовые поля от HTML
            cleaned_custom_data = CollectionController._sanitize_custom_data(custom_data)
            
            # Валидируем изображения
            images = data.get('images', [])
            if not isinstance(images, list):
                return jsonify({'error': 'Images must be an array'}), 400
            
            if len(images) > 20:  # Максимум 20 изображений на предмет
                return jsonify({'error': 'Maximum 20 images per item allowed'}), 400
            
            # Создаем новый предмет
            item = Item(
                collection_id=collection_id,
                custom_data=json.dumps(cleaned_custom_data),
                images=json.dumps(images)
            )
            
            db.session.add(item)
            db.session.commit()
            
            # Логируем создание предмета
            AuditLogger.log_item_action(
                action=AuditAction.ITEM_CREATE,
                item_id=item.id,
                collection_id=collection_id,
                user_id=current_user.id
            )
            
            current_app.logger.info(f'User {current_user.id} added item {item.id} to collection {collection_id}')
            
            return jsonify({
                'message': 'Item added successfully',
                'item': item.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error adding item to collection {collection_id}: {str(e)}')
            AuditLogger.log_action(
                action=AuditAction.ITEM_CREATE,
                resource_type=ResourceType.ITEM,
                details={'error': 'system_error', 'collection_id': collection_id, 'message': str(e)}
            )
            return jsonify({'error': 'Failed to add item'}), 500

    @staticmethod
    @api_read_rate_limit()
    def get_collection_items(collection_id):
        """Получение всех предметов коллекции"""
        try:
            # Валидируем ID коллекции
            try:
                collection_id = int(collection_id)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid collection ID'}), 400
            
            # Получаем коллекцию
            collection = Collection.query.get(collection_id)
            
            if not collection:
                return jsonify({'error': 'Collection not found'}), 404
            
            # Проверяем права доступа для приватных коллекций
            if not collection.is_public and (not current_user.is_authenticated or collection.user_id != current_user.id):
                AuditLogger.log_action(
                    action=AuditAction.ITEM_VIEW,
                    resource_type=ResourceType.ITEM,
                    details={'error': 'access_denied', 'collection_id': collection_id}
                )
                return jsonify({'error': 'Access denied'}), 403
            
            # Параметры пагинации и фильтрации
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 50, type=int), 100)
            
            # Получаем предметы коллекции с пагинацией
            items_query = Item.query.filter_by(collection_id=collection_id)
            
            # Сортировка
            sort_by = request.args.get('sort', 'created_at')
            if sort_by == 'updated_at':
                items_query = items_query.order_by(Item.updated_at.desc())
            else:
                items_query = items_query.order_by(Item.created_at.desc())
            
            pagination = items_query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            items = pagination.items
            
            # Логируем просмотр предметов коллекции
            AuditLogger.log_action(
                action=AuditAction.ITEM_VIEW,
                resource_type=ResourceType.ITEM,
                details={
                    'action': 'list_collection_items',
                    'collection_id': collection_id,
                    'items_count': len(items)
                }
            )
            
            return jsonify({
                'items': [item.to_dict() for item in items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                },
                'collection': {
                    'id': collection.id,
                    'name': collection.name,
                    'custom_fields': collection.get_custom_fields()
                }
            }), 200
            
        except Exception as e:
            current_app.logger.error(f'Error getting items for collection {collection_id}: {str(e)}')
            return jsonify({'error': 'Failed to retrieve items'}), 500

    @staticmethod
    @login_required
    @api_write_rate_limit()
    @validate_json_input(
        optional_fields={
            'custom_data': lambda x: (True, "Valid") if isinstance(x, dict) else (False, "custom_data must be an object"),
            'images': lambda x: (True, "Valid") if isinstance(x, list) else (False, "images must be an array")
        }
    )
    def update_item(item_id):
        """Обновление предмета"""
        try:
            # Валидируем ID предмета
            try:
                item_id = int(item_id)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid item ID'}), 400
            
            # Получаем предмет
            item = Item.query.get(item_id)
            
            if not item:
                return jsonify({'error': 'Item not found'}), 404
            
            # Проверяем права доступа через коллекцию
            if item.collection.user_id != current_user.id:
                AuditLogger.log_action(
                    action=AuditAction.ITEM_UPDATE,
                    resource_type=ResourceType.ITEM,
                    resource_id=item_id,
                    details={'error': 'access_denied'}
                )
                return jsonify({'error': 'Access denied'}), 403
            
            data = request.get_json()
            changes = {}
            
            # Валидируем и обновляем данные, если обновляются кастомные поля
            if 'custom_data' in data:
                validation_result = CollectionController._validate_item_data(
                    data['custom_data'], 
                    item.collection.get_custom_fields()
                )
                
                if not validation_result['valid']:
                    return jsonify({'error': validation_result['error']}), 400
                
                # Очищаем данные
                cleaned_custom_data = CollectionController._sanitize_custom_data(data['custom_data'])
                item.custom_data = json.dumps(cleaned_custom_data)
                changes['custom_data'] = cleaned_custom_data
            
            # Обновляем изображения, если переданы
            if 'images' in data:
                images = data['images']
                if not isinstance(images, list):
                    return jsonify({'error': 'Images must be an array'}), 400
                
                if len(images) > 20:
                    return jsonify({'error': 'Maximum 20 images per item allowed'}), 400
                
                item.images = json.dumps(images)
                changes['images'] = images
            
            # Обновляем timestamp
            item.updated_at = db.func.now()
            
            db.session.commit()
            
            # Логируем обновление предмета
            AuditLogger.log_item_action(
                action=AuditAction.ITEM_UPDATE,
                item_id=item.id,
                collection_id=item.collection_id,
                user_id=current_user.id
            )
            
            current_app.logger.info(f'User {current_user.id} updated item {item.id}')
            
            return jsonify({
                'message': 'Item updated successfully',
                'item': item.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error updating item {item_id}: {str(e)}')
            AuditLogger.log_action(
                action=AuditAction.ITEM_UPDATE,
                resource_type=ResourceType.ITEM,
                resource_id=item_id,
                details={'error': 'system_error', 'message': str(e)}
            )
            return jsonify({'error': 'Failed to update item'}), 500

    @staticmethod
    @login_required
    @api_delete_rate_limit()
    def delete_item(item_id):
        """Удаление предмета"""
        try:
            # Валидируем ID предмета
            try:
                item_id = int(item_id)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid item ID'}), 400
            
            # Получаем предмет
            item = Item.query.get(item_id)
            
            if not item:
                return jsonify({'error': 'Item not found'}), 404
            
            # Проверяем права доступа через коллекцию
            if item.collection.user_id != current_user.id:
                AuditLogger.log_action(
                    action=AuditAction.ITEM_DELETE,
                    resource_type=ResourceType.ITEM,
                    resource_id=item_id,
                    details={'error': 'access_denied'}
                )
                return jsonify({'error': 'Access denied'}), 403
            
            # Сохраняем информацию для логирования
            collection_id = item.collection_id
            
            db.session.delete(item)
            db.session.commit()
            
            # Логируем удаление предмета
            AuditLogger.log_action(
                action=AuditAction.ITEM_DELETE,
                resource_type=ResourceType.ITEM,
                resource_id=item_id,
                user_id=current_user.id,
                details={'collection_id': collection_id}
            )
            
            current_app.logger.info(f'User {current_user.id} deleted item {item_id}')
            
            return jsonify({
                'message': 'Item deleted successfully'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error deleting item {item_id}: {str(e)}')
            AuditLogger.log_action(
                action=AuditAction.ITEM_DELETE,
                resource_type=ResourceType.ITEM,
                resource_id=item_id,
                details={'error': 'system_error', 'message': str(e)}
            )
            return jsonify({'error': 'Failed to delete item'}), 500

    @staticmethod
    @api_read_rate_limit()
    def get_item_by_id(item_id):
        """Получение конкретного предмета по ID"""
        try:
            # Валидируем ID предмета
            try:
                item_id = int(item_id)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid item ID'}), 400
            
            item = Item.query.get(item_id)
            
            if not item:
                return jsonify({'error': 'Item not found'}), 404
            
            # Проверяем права доступа через коллекцию
            collection = item.collection
            if not collection.is_public and (not current_user.is_authenticated or collection.user_id != current_user.id):
                AuditLogger.log_action(
                    action=AuditAction.ITEM_VIEW,
                    resource_type=ResourceType.ITEM,
                    resource_id=item_id,
                    details={'error': 'access_denied'}
                )
                return jsonify({'error': 'Access denied'}), 403
            
            # Логируем просмотр предмета
            AuditLogger.log_item_action(
                action=AuditAction.ITEM_VIEW,
                item_id=item.id,
                collection_id=item.collection_id,
                user_id=current_user.id if current_user.is_authenticated else None
            )
            
            return jsonify({
                'item': item.to_dict(),
                'collection': {
                    'id': collection.id,
                    'name': collection.name,
                    'custom_fields': collection.get_custom_fields()
                }
            }), 200
            
        except Exception as e:
            current_app.logger.error(f'Error getting item {item_id}: {str(e)}')
            return jsonify({'error': 'Failed to retrieve item'}), 500

    @staticmethod
    def _validate_item_data(item_data, collection_fields):
        """Валидация данных предмета согласно кастомным полям коллекции"""
        try:
            if not collection_fields:
                return {'valid': True}
            
            for field in collection_fields:
                field_name = field.get('name')
                field_type = field.get('type')
                is_required = field.get('required', False)
                
                if not field_name or not field_type:
                    continue
                
                # Проверяем обязательные поля
                if is_required:
                    if field_name not in item_data or not str(item_data[field_name]).strip():
                        return {
                            'valid': False,
                            'error': f'Required field "{field_name}" is missing or empty'
                        }
                
                # Проверяем типы данных, если поле заполнено
                if field_name in item_data and item_data[field_name] is not None:
                    value = item_data[field_name]
                    
                    if field_type == 'number':
                        try:
                            float(value)
                        except (ValueError, TypeError):
                            return {
                                'valid': False,
                                'error': f'Field "{field_name}" must be a valid number'
                            }
                    
                    elif field_type == 'date':
                        # Проверка формата даты (можно расширить)
                        if not isinstance(value, str) or len(value.strip()) < 8:
                            return {
                                'valid': False,
                                'error': f'Field "{field_name}" must be a valid date'
                            }
                        
                        # Дополнительная проверка формата даты
                        try:
                            from datetime import datetime
                            # Пробуем несколько популярных форматов
                            formats = ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']
                            parsed = False
                            for fmt in formats:
                                try:
                                    datetime.strptime(value.strip(), fmt)
                                    parsed = True
                                    break
                                except ValueError:
                                    continue
                            
                            if not parsed:
                                return {
                                    'valid': False,
                                    'error': f'Field "{field_name}" has invalid date format'
                                }
                        except Exception:
                            pass  # Если не удалось распарсить, пропускаем детальную проверку
                    
                    elif field_type == 'checkbox':
                        if not isinstance(value, bool):
                            return {
                                'valid': False,
                                'error': f'Field "{field_name}" must be a boolean value'
                            }
                    
                    elif field_type == 'text':
                        if not isinstance(value, str):
                            return {
                                'valid': False,
                                'error': f'Field "{field_name}" must be a text string'
                            }
                        
                        # Проверяем длину текста
                        if len(value) > SecurityValidator.MAX_TEXT_LENGTH:
                            return {
                                'valid': False,
                                'error': f'Field "{field_name}" is too long (max {SecurityValidator.MAX_TEXT_LENGTH} characters)'
                            }
                    
                    elif field_type == 'image':
                        if not isinstance(value, str):
                            return {
                                'valid': False,
                                'error': f'Field "{field_name}" must be a string (image URL)'
                            }
            
            return {'valid': True}
            
        except Exception as e:
            current_app.logger.error(f'Validation error: {str(e)}')
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }

    @staticmethod
    def _sanitize_custom_data(custom_data):
        """Очистка кастомных данных от потенциально опасного контента"""
        if not isinstance(custom_data, dict):
            return custom_data
        
        sanitized_data = {}
        
        for key, value in custom_data.items():
            # Очищаем ключ
            clean_key = sanitize_html(str(key))
            
            if isinstance(value, str):
                # Очищаем строковые значения от HTML
                clean_value = sanitize_html(value)
                
                # Дополнительная проверка на длину
                if len(clean_value) > SecurityValidator.MAX_TEXT_LENGTH:
                    clean_value = clean_value[:SecurityValidator.MAX_TEXT_LENGTH]
                
                sanitized_data[clean_key] = clean_value
            
            elif isinstance(value, (int, float, bool)):
                # Числа и булевы значения оставляем как есть
                sanitized_data[clean_key] = value
            
            elif isinstance(value, list):
                # Для списков очищаем каждый элемент
                clean_list = []
                for item in value[:100]:  # Ограничиваем до 100 элементов
                    if isinstance(item, str):
                        clean_item = sanitize_html(item)
                        if len(clean_item) <= SecurityValidator.MAX_TEXT_LENGTH:
                            clean_list.append(clean_item)
                    elif isinstance(item, (int, float, bool)):
                        clean_list.append(item)
                
                sanitized_data[clean_key] = clean_list
            
            else:
                # Для других типов данных преобразуем в строку и очищаем
                clean_value = sanitize_html(str(value))
                if len(clean_value) <= SecurityValidator.MAX_TEXT_LENGTH:
                    sanitized_data[clean_key] = clean_value
        
        return sanitized_data

    # ========== ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ==========

    @staticmethod
    @api_read_rate_limit()
    def get_public_collections():
        """Получение списка публичных коллекций"""
        try:
            # Параметры пагинации
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)
            
            # Поисковый запрос
            search = request.args.get('search', '').strip()
            
            # Базовый запрос для публичных коллекций
            query = Collection.query.filter_by(is_public=True)
            
            # Добавляем поиск если указан
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    db.or_(
                        Collection.name.ilike(search_term),
                        Collection.description.ilike(search_term)
                    )
                )
            
            # Сортировка
            sort_by = request.args.get('sort', 'created_at')
            if sort_by == 'name':
                query = query.order_by(Collection.name)
            elif sort_by == 'updated_at':
                query = query.order_by(Collection.updated_at.desc())
            else:
                query = query.order_by(Collection.created_at.desc())
            
            # Пагинация
            pagination = query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            collections = pagination.items
            
            # Логируем просмотр публичных коллекций
            AuditLogger.log_action(
                action=AuditAction.COLLECTION_VIEW,
                resource_type=ResourceType.COLLECTION,
                details={
                    'action': 'list_public_collections',
                    'search': search,
                    'count': len(collections)
                }
            )
            
            return jsonify({
                'collections': [collection.to_dict() for collection in collections],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                },
                'search': search
            }), 200
            
        except Exception as e:
            current_app.logger.error(f'Error getting public collections: {str(e)}')
            return jsonify({'error': 'Failed to retrieve public collections'}), 500

    @staticmethod
    @login_required
    @api_write_rate_limit()
    def share_collection(collection_id):
        """Создание публичной ссылки для коллекции"""
        try:
            # Валидируем ID коллекции
            try:
                collection_id = int(collection_id)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid collection ID'}), 400
            
            collection = Collection.query.get(collection_id)
            
            if not collection:
                return jsonify({'error': 'Collection not found'}), 404
            
            # Проверяем права доступа
            if collection.user_id != current_user.id:
                return jsonify({'error': 'Access denied'}), 403
            
            # Делаем коллекцию публичной если она не была таковой
            if not collection.is_public:
                collection.is_public = True
                db.session.commit()
            
            # Логируем создание публичной ссылки
            AuditLogger.log_collection_action(
                action=AuditAction.COLLECTION_SHARE,
                collection_id=collection.id,
                collection_name=collection.name,
                user_id=current_user.id
            )
            
            # Генерируем публичную ссылку
            from flask import url_for
            public_url = url_for('collections.view_collection', collection_id=collection.id, _external=True)
            
            return jsonify({
                'message': 'Collection shared successfully',
                'public_url': public_url,
                'is_public': True
            }), 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error sharing collection {collection_id}: {str(e)}')
            return jsonify({'error': 'Failed to share collection'}), 500