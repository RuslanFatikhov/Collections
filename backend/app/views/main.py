from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import current_user, login_required
from app.models import db, Collection, User

# Create main blueprint
main_routes = Blueprint('main', __name__)

@main_routes.route('/')
def index():
    """Home page"""
    # Get recent public collections
    recent_collections = Collection.get_public_collections(limit=6)
    
    return render_template('index.html', 
                         recent_collections=recent_collections,
                         current_user=current_user)

@main_routes.route('/collection/<uuid>')
def view_collection(uuid):
    """View public collection by UUID"""
    collection = Collection.find_by_uuid(uuid)
    
    if not collection:
        return render_template('404.html'), 404
    
    # Check if collection is public or if user is owner
    if not collection.is_public and (not current_user.is_authenticated or current_user.id != collection.user_id):
        return render_template('403.html'), 403
    
    return render_template('collection_view.html', 
                         collection=collection,
                         items=collection.items,
                         custom_fields=collection.get_custom_fields())

@main_routes.route('/profile')
@login_required
def profile():
    """User profile page"""
    user_collections = current_user.collections
    
    return render_template('profile.html',
                         user=current_user,
                         collections=user_collections)

@main_routes.route('/explore')
def explore():
    """Explore public collections"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    collections_query = Collection.query.filter_by(is_public=True).order_by(Collection.created_at.desc())
    collections = collections_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('explore.html', collections=collections)

@main_routes.route('/search')
def search():
    """Search collections"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    if not query:
        return redirect(url_for('main.explore'))
    
    # Search in public collections
    collections_query = Collection.query.filter(
        Collection.is_public == True,
        Collection.title.contains(query) | Collection.description.contains(query)
    ).order_by(Collection.created_at.desc())
    
    collections = collections_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('search.html', 
                         collections=collections, 
                         query=query)

@main_routes.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@main_routes.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'database': 'connected' if db.engine else 'disconnected'
    })

# Error handlers
@main_routes.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@main_routes.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

@main_routes.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500