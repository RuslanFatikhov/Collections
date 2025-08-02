from datetime import datetime
import json
from app import db

class Item(db.Model):
    __tablename__ = 'items'
    
    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(db.Integer, db.ForeignKey('collections.id'), nullable=False, index=True)
    custom_data = db.Column(db.Text, nullable=True)  # JSON string with custom field values
    images = db.Column(db.Text, nullable=True)  # JSON array of image paths
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    collection = db.relationship('Collection', back_populates='items')
    
    def __repr__(self):
        return f'<Item {self.id} in Collection {self.collection.title if self.collection else "Unknown"}>'
    
    def to_dict(self):
        """Convert item object to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'collection_id': self.collection_id,
            'custom_data': self.get_custom_data(),
            'images': self.get_images(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_custom_data(self):
        """Parse and return custom data as Python object"""
        if not self.custom_data:
            return {}
        try:
            return json.loads(self.custom_data)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_custom_data(self, data):
        """Set custom data from Python object"""
        if data is None:
            self.custom_data = None
        else:
            self.custom_data = json.dumps(data, ensure_ascii=False)
    
    def get_images(self):
        """Parse and return images as Python list"""
        if not self.images:
            return []
        try:
            return json.loads(self.images)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_images(self, images_list):
        """Set images from Python list"""
        if images_list is None:
            self.images = None
        else:
            self.images = json.dumps(images_list, ensure_ascii=False)
    
    def add_image(self, image_path):
        """Add single image to the list"""
        current_images = self.get_images()
        current_images.append(image_path)
        self.set_images(current_images)
    
    def remove_image(self, image_path):
        """Remove single image from the list"""
        current_images = self.get_images()
        if image_path in current_images:
            current_images.remove(image_path)
            self.set_images(current_images)
    
    def get_field_value(self, field_name):
        """Get value of specific custom field"""
        data = self.get_custom_data()
        return data.get(field_name)
    
    def set_field_value(self, field_name, value):
        """Set value of specific custom field"""
        data = self.get_custom_data()
        data[field_name] = value
        self.set_custom_data(data)
    
    def get_main_image(self):
        """Get first image as main image"""
        images = self.get_images()
        return images[0] if images else None
    
    def validate_against_collection_fields(self):
        """Validate item data against collection's custom fields"""
        if not self.collection:
            return False
        
        collection_fields = self.collection.get_custom_fields()
        item_data = self.get_custom_data()
        
        # Check required fields
        for field in collection_fields:
            field_name = field.get('name')
            is_required = field.get('required', False)
            
            if is_required and (field_name not in item_data or not item_data[field_name]):
                return False
        
        return True