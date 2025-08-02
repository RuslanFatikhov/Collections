from flask import Blueprint
from app.controllers.collection_controller import CollectionController

# Создаем Blueprint для коллекций
collections_bp = Blueprint('collections', __name__)

# POST /api/collections - создание новой коллекции
@collections_bp.route('/api/collections', methods=['POST'])
def create_collection():
    return CollectionController.create_collection()

# GET /api/collections - получение всех коллекций пользователя
@collections_bp.route('/api/collections', methods=['GET'])
def get_user_collections():
    return CollectionController.get_user_collections()

# GET /api/collections/<id> - получение конкретной коллекции
@collections_bp.route('/api/collections/<int:collection_id>', methods=['GET'])
def get_collection(collection_id):
    return CollectionController.get_collection_by_id(collection_id)

# PUT /api/collections/<id> - обновление коллекции
@collections_bp.route('/api/collections/<int:collection_id>', methods=['PUT'])
def update_collection(collection_id):
    return CollectionController.update_collection(collection_id)

# DELETE /api/collections/<id> - удаление коллекции
@collections_bp.route('/api/collections/<int:collection_id>', methods=['DELETE'])
def delete_collection(collection_id):
    return CollectionController.delete_collection(collection_id)

# ========== НОВЫЕ МАРШРУТЫ ДЛЯ ПУБЛИЧНЫХ ССЫЛОК ==========

# GET /api/public/<uuid> - получение коллекции по публичной ссылке
@collections_bp.route('/api/public/<string:public_uuid>', methods=['GET'])
def get_public_collection(public_uuid):
    return CollectionController.get_collection_by_public_uuid(public_uuid)

# POST /api/collections/<id>/toggle-public - переключение публичности коллекции
@collections_bp.route('/api/collections/<int:collection_id>/toggle-public', methods=['POST'])
def toggle_collection_public(collection_id):
    return CollectionController.toggle_collection_public(collection_id)

# POST /api/collections/<id>/regenerate-uuid - перегенерация публичного UUID
@collections_bp.route('/api/collections/<int:collection_id>/regenerate-uuid', methods=['POST'])
def regenerate_public_uuid(collection_id):
    return CollectionController.regenerate_public_uuid(collection_id)

# ========== МАРШРУТЫ ДЛЯ РАБОТЫ С ПРЕДМЕТАМИ КОЛЛЕКЦИЙ ==========

# POST /api/collections/<id>/items - добавление предмета в коллекцию
@collections_bp.route('/api/collections/<int:collection_id>/items', methods=['POST'])
def add_item_to_collection(collection_id):
    return CollectionController.add_item_to_collection(collection_id)

# GET /api/collections/<id>/items - получение всех предметов коллекции
@collections_bp.route('/api/collections/<int:collection_id>/items', methods=['GET'])
def get_collection_items(collection_id):
    return CollectionController.get_collection_items(collection_id)

# PUT /api/items/<id> - обновление предмета
@collections_bp.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    return CollectionController.update_item(item_id)

# DELETE /api/items/<id> - удаление предмета
@collections_bp.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    return CollectionController.delete_item(item_id)

# GET /api/items/<id> - получение конкретного предмета
@collections_bp.route('/api/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    return CollectionController.get_item_by_id(item_id)