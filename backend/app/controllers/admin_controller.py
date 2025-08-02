from flask import jsonify, request
from app.models.user import User
from app.models.collection import Collection
from app.models.admin import Admin, db
from datetime import datetime
from sqlalchemy import desc

class AdminController:
    
    @staticmethod
    def get_users():
        """
        Получить список всех пользователей
        """
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            search = request.args.get('search', '', type=str)
            
            # Базовый запрос
            query = User.query
            
            # Поиск по имени или email
            if search:
                query = query.filter(
                    db.or_(
                        User.name.ilike(f'%{search}%'),
                        User.email.ilike(f'%{search}%')
                    )
                )
            
            # Пагинация
            users = query.order_by(desc(User.created_at)).paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            return jsonify({
                'users': [user.to_dict() for user in users.items],
                'total': users.total,
                'pages': users.pages,
                'current_page': page,
                'per_page': per_page
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    def get_collections():
        """
        Получить список всех коллекций
        """
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            search = request.args.get('search', '', type=str)
            
            # Базовый запрос с join для получения данных пользователя
            query = Collection.query.join(User)
            
            # Поиск по названию коллекции или имени пользователя
            if search:
                query = query.filter(
                    db.or_(
                        Collection.name.ilike(f'%{search}%'),
                        User.name.ilike(f'%{search}%')
                    )
                )
            
            # Пагинация
            collections = query.order_by(desc(Collection.created_at)).paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            # Формируем ответ с данными пользователя
            collections_data = []
            for collection in collections.items:
                collection_dict = collection.to_dict()
                collection_dict['user'] = {
                    'id': collection.user.id,
                    'name': collection.user.name,
                    'email': collection.user.email
                }
                collections_data.append(collection_dict)
            
            return jsonify({
                'collections': collections_data,
                'total': collections.total,
                'pages': collections.pages,
                'current_page': page,
                'per_page': per_page
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    def block_user(user_id):
        """
        Заблокировать пользователя
        """
        try:
            user = User.query.get_or_404(user_id)
            user.is_blocked = True
            user.blocked_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'message': f'User {user.name} has been blocked',
                'user': user.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    def unblock_user(user_id):
        """
        Разблокировать пользователя
        """
        try:
            user = User.query.get_or_404(user_id)
            user.is_blocked = False
            user.blocked_at = None
            db.session.commit()
            
            return jsonify({
                'message': f'User {user.name} has been unblocked',
                'user': user.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    def block_collection(collection_id):
        """
        Заблокировать коллекцию
        """
        try:
            collection = Collection.query.get_or_404(collection_id)
            collection.is_blocked = True
            collection.blocked_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'message': f'Collection "{collection.name}" has been blocked',
                'collection': collection.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    def unblock_collection(collection_id):
        """
        Разблокировать коллекцию
        """
        try:
            collection = Collection.query.get_or_404(collection_id)
            collection.is_blocked = False
            collection.blocked_at = None
            db.session.commit()
            
            return jsonify({
                'message': f'Collection "{collection.name}" has been unblocked',
                'collection': collection.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    def get_stats():
        """
        Получить общую статистику
        """
        try:
            total_users = User.query.count()
            blocked_users = User.query.filter_by(is_blocked=True).count()
            total_collections = Collection.query.count()
            blocked_collections = Collection.query.filter_by(is_blocked=True).count()
            
            # Пользователи за последние 30 дней
            thirty_days_ago = datetime.utcnow().replace(day=1)  # Упрощенно - начало месяца
            new_users_month = User.query.filter(User.created_at >= thirty_days_ago).count()
            
            # Коллекции за последние 30 дней
            new_collections_month = Collection.query.filter(
                Collection.created_at >= thirty_days_ago
            ).count()
            
            return jsonify({
                'total_users': total_users,
                'blocked_users': blocked_users,
                'active_users': total_users - blocked_users,
                'total_collections': total_collections,
                'blocked_collections': blocked_collections,
                'active_collections': total_collections - blocked_collections,
                'new_users_month': new_users_month,
                'new_collections_month': new_collections_month
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500