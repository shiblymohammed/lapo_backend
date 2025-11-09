"""Custom storage backends for secure file handling"""
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os
import uuid
import hashlib
from pathlib import Path


class SecureFileStorage(FileSystemStorage):
    """
    Secure file storage that:
    1. Stores files outside the web root
    2. Uses secure random file naming
    3. Sets proper file permissions
    4. Organizes files by type and date
    """
    
    def __init__(self, *args, **kwargs):
        # Set location outside web root if not specified
        if 'location' not in kwargs:
            kwargs['location'] = settings.SECURE_MEDIA_ROOT
        
        # Disable direct URL access by default
        if 'base_url' not in kwargs:
            kwargs['base_url'] = None
        
        super().__init__(*args, **kwargs)
    
    def get_available_name(self, name, max_length=None):
        """
        Generate a secure, unique filename to prevent:
        - File overwrites
        - Path traversal attacks
        - Predictable file names
        """
        # Get file extension
        ext = os.path.splitext(name)[1].lower()
        
        # Generate secure random filename
        random_name = uuid.uuid4().hex
        
        # Add timestamp hash for additional uniqueness
        timestamp_hash = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:8]
        
        # Combine to create secure filename
        secure_name = f"{random_name}_{timestamp_hash}{ext}"
        
        return secure_name
    
    def _save(self, name, content):
        """Save file with secure permissions"""
        # Get the full path
        full_path = self.path(name)
        
        # Ensure directory exists
        directory = os.path.dirname(full_path)
        os.makedirs(directory, mode=0o750, exist_ok=True)
        
        # Save the file
        name = super()._save(name, content)
        
        # Set secure file permissions (read/write for owner only)
        full_path = self.path(name)
        os.chmod(full_path, 0o640)
        
        return name


class ProductImageStorage(SecureFileStorage):
    """Storage for product images with organized directory structure"""
    
    def __init__(self, *args, **kwargs):
        kwargs['location'] = os.path.join(settings.SECURE_MEDIA_ROOT, 'products', 'images')
        super().__init__(*args, **kwargs)
    
    def get_available_name(self, name, max_length=None):
        """Organize images by date"""
        from datetime import datetime
        
        # Get secure base name
        secure_name = super().get_available_name(name, max_length)
        
        # Organize by year/month
        date_path = datetime.now().strftime('%Y/%m')
        
        return os.path.join(date_path, secure_name)


class ProductThumbnailStorage(SecureFileStorage):
    """Storage for product thumbnails"""
    
    def __init__(self, *args, **kwargs):
        kwargs['location'] = os.path.join(settings.SECURE_MEDIA_ROOT, 'products', 'thumbnails')
        super().__init__(*args, **kwargs)
    
    def get_available_name(self, name, max_length=None):
        """Organize thumbnails by date"""
        from datetime import datetime
        
        secure_name = super().get_available_name(name, max_length)
        date_path = datetime.now().strftime('%Y/%m')
        
        return os.path.join(date_path, secure_name)


class DynamicResourceStorage(SecureFileStorage):
    """Storage for user-uploaded dynamic resources"""
    
    def __init__(self, *args, **kwargs):
        kwargs['location'] = os.path.join(settings.SECURE_MEDIA_ROOT, 'resources', 'dynamic')
        super().__init__(*args, **kwargs)
    
    def get_available_name(self, name, max_length=None):
        """Organize resources by date and type"""
        from datetime import datetime
        
        secure_name = super().get_available_name(name, max_length)
        
        # Organize by year/month
        date_path = datetime.now().strftime('%Y/%m')
        
        # Separate by file type
        ext = os.path.splitext(name)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
            type_folder = 'images'
        elif ext in ['.pdf', '.docx', '.doc']:
            type_folder = 'documents'
        else:
            type_folder = 'other'
        
        return os.path.join(date_path, type_folder, secure_name)


class OrderResourceStorage(SecureFileStorage):
    """Storage for order-specific resources (candidate photos, logos, etc.)"""
    
    def __init__(self, *args, **kwargs):
        kwargs['location'] = os.path.join(settings.SECURE_MEDIA_ROOT, 'resources', 'orders')
        super().__init__(*args, **kwargs)
    
    def get_available_name(self, name, max_length=None):
        """Organize order resources by date"""
        from datetime import datetime
        
        secure_name = super().get_available_name(name, max_length)
        date_path = datetime.now().strftime('%Y/%m')
        
        return os.path.join(date_path, secure_name)


def get_secure_file_path(instance, filename, subfolder=''):
    """
    Generate secure file path for uploads.
    Can be used as upload_to parameter in FileField/ImageField.
    
    Usage:
        image = models.ImageField(upload_to=lambda i, f: get_secure_file_path(i, f, 'images'))
    """
    # Generate secure filename
    ext = os.path.splitext(filename)[1].lower()
    secure_name = f"{uuid.uuid4().hex}{ext}"
    
    # Organize by date
    from datetime import datetime
    date_path = datetime.now().strftime('%Y/%m/%d')
    
    # Combine path
    if subfolder:
        return os.path.join(subfolder, date_path, secure_name)
    return os.path.join(date_path, secure_name)
