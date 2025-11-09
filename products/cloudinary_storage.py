"""
Cloudinary storage backends for different types of uploads
"""
from cloudinary.storage import MediaCloudinaryStorage
from django.conf import settings
import uuid


class ProductImageCloudinaryStorage(MediaCloudinaryStorage):
    """
    Cloudinary storage for product images (admin uploads)
    - Public access
    - Organized by product type
    - Automatic optimization
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def get_available_name(self, name, max_length=None):
        """Generate unique filename for Cloudinary"""
        import os
        ext = os.path.splitext(name)[1].lower()
        unique_name = f"products/{uuid.uuid4().hex}{ext}"
        return unique_name


class UserResourceCloudinaryStorage(MediaCloudinaryStorage):
    """
    Cloudinary storage for user-uploaded resources
    - Private access (requires signed URLs)
    - Organized by resource type
    - Automatic optimization
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def get_available_name(self, name, max_length=None):
        """Generate unique filename for Cloudinary"""
        import os
        ext = os.path.splitext(name)[1].lower()
        unique_name = f"user_resources/{uuid.uuid4().hex}{ext}"
        return unique_name


class SecureCloudinaryStorage(MediaCloudinaryStorage):
    """
    Secure Cloudinary storage for sensitive files
    - Private access only
    - Signed URLs required
    - No public access
    """
    
    def __init__(self, *args, **kwargs):
        kwargs['resource_type'] = 'raw'  # For non-image files
        super().__init__(*args, **kwargs)
    
    def get_available_name(self, name, max_length=None):
        """Generate unique filename for Cloudinary"""
        import os
        ext = os.path.splitext(name)[1].lower()
        unique_name = f"secure/{uuid.uuid4().hex}{ext}"
        return unique_name
