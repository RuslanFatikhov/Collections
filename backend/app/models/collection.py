from datetime import datetime
import json
import uuid
from app import db

class Collection(db.Model):
    __tablename__ = 'collections'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    public_uuid = db.Column(db.String(36), unique=True, nullable=True, index=True)  # For public sharing
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)  # Изменил с title на name для консистентности
    description = db.Column(db.Text, nullable=True)
    cover_url = db.Column(db.String(255), nullable=True)  # Изменил с cover_image на cover_url
    custom_fields = db.Column(db.Text, nullable=True)  # JSON string with field definitions
    is_public = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)
    blocked_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', back_populates='collections')
    items = db.relationship('Item', back_populates='collection', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Collection {self.name} by {self.user.name if self.user else "Unknown"}>'
    
    def to_dict(self, include_items=False, public_view=False):
        """Convert collection object to dictionary for JSON serialization"""
        result = {
            'id': self.id,
            'uuid': self.uuid,
            'user_id': self.user_id,
            'name': self.name,
            'title': self.name,  # Для обратной совместимости
            'description': self.description,
            'cover_url': self.cover_url,
            'cover_image': self.cover_url,  # Для обратной совместимости
            'custom_fields': self.get_custom_fields(),
            'is_public': self.is_public,
            'is_blocked': self.is_blocked,
            'blocked_at': self.blocked_at.isoformat() if self.blocked_at else None,
            'items_count': self.get_items_count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # Add public URL if collection is public
        if self.is_public and self.public_uuid:
            result['public_url'] = self.get_public_url()
            result['public_uuid'] = self.public_uuid
        
        # For public view, add user info but hide sensitive data
        if public_view and self.user:
            result['user'] = {
                'name': self.user.name,
                'avatar': getattr(self.user, 'avatar', None)
            }
        
        if include_items:
            result['items'] = [item.to_dict() for item in self.items]
        
        return result
    
    def get_custom_fields(self):
        """Parse and return custom fields as Python object"""
        if not self.custom_fields:
            return []
        try:
            return json.loads(self.custom_fields)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_custom_fields(self, fields_data):
        """Set custom fields from Python object"""
        if fields_data is None:
            self.custom_fields = None
        else:
            self.custom_fields = json.dumps(fields_data, ensure_ascii=False)
    
    def get_items_count(self):
        """Get total number of items in this collection"""
        return len(self.items)
    
    def get_public_url(self):
        """Get public URL for this collection"""
        if self.public_uuid:
            return f"/public/{self.public_uuid}"
        return None
    
    def generate_public_uuid(self):
        """Generate a new public UUID for sharing"""
        self.public_uuid = str(uuid.uuid4())
        return self.public_uuid
    
    def regenerate_public_uuid(self):
        """Regenerate public UUID for security purposes"""
        if self.is_public:
            return self.generate_public_uuid()
        return None
    
    def toggle_public(self):
        """Toggle public status and manage public UUID"""
        self.is_public = not self.is_public
        
        if self.is_public and not self.public_uuid:
            # Generate public UUID when making collection public
            self.generate_public_uuid()
        elif not self.is_public:
            # Keep the UUID but collection won't be accessible
            # This allows re-enabling without changing the link
            pass
            
        return self.is_public
    
    @staticmethod
    def find_by_uuid(collection_uuid):
        """Find collection by UUID"""
        return Collection.query.filter_by(uuid=collection_uuid).first()
    
    @staticmethod
    def find_by_public_uuid(public_uuid):
        """Find public collection by public UUID"""
        return Collection.query.filter_by(
            public_uuid=public_uuid, 
            is_public=True
        ).first()
    
    @staticmethod
    def get_public_collections(limit=None):
        """Get all public collections"""
        query = Collection.query.filter_by(is_public=True, is_blocked=False).order_by(Collection.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def validate_custom_fields(self):
        """Validate custom fields structure"""
        fields = self.get_custom_fields()
        if not isinstance(fields, list):
            return False
        
        for field in fields:
            if not isinstance(field, dict):
                return False
            if 'name' not in field or 'type' not in field:
                return False
            if field['type'] not in ['text', 'number', 'date', 'image', 'checkbox']:
                return False
        
        return True