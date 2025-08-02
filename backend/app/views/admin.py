from flask import Blueprint, render_template, jsonify
from app.controllers.admin_controller import AdminController
from app.utils.admin_middleware import admin_required, admin_page_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')

# HTML страницы для администратора
@admin_bp.route('/')
@admin_page_required
def dashboard():
    """
    Главная страница административной панели
    """
    return render_template('admin.html')

# API endpoints для администратора

@admin_api_bp.route('/stats')
@admin_required
def get_stats():
    """
    GET /api/admin/stats - получить общую статистику
    """
    return AdminController.get_stats()

@admin_api_bp.route('/users')
@admin_required
def get_users():
    """
    GET /api/admin/users - получить список всех пользователей
    Параметры: page, per_page, search
    """
    return AdminController.get_users()

@admin_api_bp.route('/collections')
@admin_required
def get_collections():
    """
    GET /api/admin/collections - получить список всех коллекций
    Параметры: page, per_page, search
    """
    return AdminController.get_collections()

@admin_api_bp.route('/users/<int:user_id>/block', methods=['POST'])
@admin_required
def block_user(user_id):
    """
    POST /api/admin/users/<id>/block - заблокировать пользователя
    """
    return AdminController.block_user(user_id)

@admin_api_bp.route('/users/<int:user_id>/unblock', methods=['POST'])
@admin_required
def unblock_user(user_id):
    """
    POST /api/admin/users/<id>/unblock - разблокировать пользователя
    """
    return AdminController.unblock_user(user_id)

@admin_api_bp.route('/collections/<int:collection_id>/block', methods=['POST'])
@admin_required
def block_collection(collection_id):
    """
    POST /api/admin/collections/<id>/block - заблокировать коллекцию
    """
    return AdminController.block_collection(collection_id)

@admin_api_bp.route('/collections/<int:collection_id>/unblock', methods=['POST'])
@admin_required
def unblock_collection(collection_id):
    """
    POST /api/admin/collections/<id>/unblock - разблокировать коллекцию
    """
    return AdminController.unblock_collection(collection_id)