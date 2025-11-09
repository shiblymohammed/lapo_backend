from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from authentication.models import CustomUser
import os
from .validators import validate_image_file


class Package(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    features = models.JSONField(default=list, help_text='List of package features')
    deliverables = models.JSONField(default=list, help_text='List of package deliverables')
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False, help_text='Mark as popular to feature on homepage')
    popular_order = models.IntegerField(default=0, help_text='Order in popular section (1-3)')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_packages')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['popular_order', '-created_at']
        indexes = [
            models.Index(fields=['is_popular', 'popular_order']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return self.name


class PackageItem(models.Model):
    package = models.ForeignKey(Package, related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.name} (x{self.quantity})"


class Campaign(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50)
    description = models.TextField()
    features = models.JSONField(default=list, help_text='List of campaign features')
    deliverables = models.JSONField(default=list, help_text='List of campaign deliverables')
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False, help_text='Mark as popular to feature on homepage')
    popular_order = models.IntegerField(default=0, help_text='Order in popular section (1-3)')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['popular_order', '-created_at']
        indexes = [
            models.Index(fields=['is_popular', 'popular_order']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return self.name


class ProductAuditLog(models.Model):
    """Audit log for tracking product changes"""
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('activate', 'Activated'),
        ('deactivate', 'Deactivated'),
    ]
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    product = GenericForeignKey('content_type', 'object_id')
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField(default=dict)  # Store what changed
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.content_type} #{self.object_id} by {self.user}"


class ResourceFieldDefinition(models.Model):
    """Dynamic resource field configuration for products"""
    FIELD_TYPE_CHOICES = [
        ('image', 'Image'),
        ('text', 'Text'),
        ('number', 'Number'),
        ('document', 'Document'),
        ('phone', 'Phone Number'),
        ('date', 'Date'),
    ]
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    product = GenericForeignKey('content_type', 'object_id')
    
    field_name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES)
    is_required = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    help_text = models.CharField(max_length=200, blank=True)
    
    # Field-specific configurations
    max_file_size_mb = models.IntegerField(null=True, blank=True)  # For image/document
    max_length = models.IntegerField(null=True, blank=True)  # For text
    min_value = models.IntegerField(null=True, blank=True)  # For number
    max_value = models.IntegerField(null=True, blank=True)  # For number
    allowed_extensions = models.JSONField(default=list, blank=True)  # For document
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ['content_type', 'object_id', 'field_name']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['order']),
        ]
    
    def __str__(self):
        return f"{self.field_name} ({self.get_field_type_display()}) for {self.content_type} #{self.object_id}"


class ChecklistTemplateItem(models.Model):
    """Template for checklist items associated with products"""
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    product = GenericForeignKey('content_type', 'object_id')
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    order = models.IntegerField(default=0)
    is_optional = models.BooleanField(default=False)
    estimated_duration_minutes = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['order']),
        ]
    
    def __str__(self):
        return f"{self.name} for {self.content_type} #{self.object_id}"


class ProductImage(models.Model):
    """Image gallery for products (packages and campaigns)"""
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    product = GenericForeignKey('content_type', 'object_id')
    
    image = models.ImageField(
        upload_to='products/images/',
        validators=[validate_image_file],
        storage=None  # Uses DEFAULT_FILE_STORAGE from settings (Cloudinary or local)
    )
    thumbnail = models.ImageField(
        upload_to='products/thumbnails/',
        blank=True,
        null=True,
        storage=None  # Uses DEFAULT_FILE_STORAGE from settings (Cloudinary or local)
    )
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    alt_text = models.CharField(max_length=200, blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', '-uploaded_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['order']),
            models.Index(fields=['is_primary']),
        ]
    
    def __str__(self):
        return f"Image for {self.content_type} #{self.object_id} (Primary: {self.is_primary})"
    
    def save(self, *args, **kwargs):
        """Ensure only one primary image per product"""
        from django.conf import settings
        import logging
        
        logger = logging.getLogger(__name__)
        
        # If this is being set as primary, unset other primary images for the same product
        if self.is_primary:
            ProductImage.objects.filter(
                content_type=self.content_type,
                object_id=self.object_id,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        
        # Skip thumbnail generation when using Cloudinary
        # Cloudinary handles thumbnail transformations automatically via URL parameters
        if self.image and settings.USE_CLOUDINARY:
            logger.info(f"Skipping thumbnail generation for ProductImage - Cloudinary handles transformations automatically")
        
        super().save(*args, **kwargs)
    
    def create_thumbnail(self):
        """Create thumbnail using Pillow (lazy import for memory optimization)"""
        # Import PIL only when needed to reduce base memory footprint
        from PIL import Image
        from io import BytesIO
        from django.core.files.uploadedfile import InMemoryUploadedFile
        import sys
        
        if not self.image:
            return None
        
        # Open the image
        img = Image.open(self.image)
        
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        
        # Create thumbnail (max 300x300)
        img.thumbnail((300, 300), Image.Resampling.LANCZOS)
        
        # Save to BytesIO
        thumb_io = BytesIO()
        img.save(thumb_io, format='JPEG', quality=85, optimize=True)
        thumb_io.seek(0)
        
        # Create filename
        original_name = os.path.basename(self.image.name)
        name_without_ext = os.path.splitext(original_name)[0]
        thumb_filename = f"{name_without_ext}_thumb.jpg"
        
        # Create InMemoryUploadedFile
        thumbnail_file = InMemoryUploadedFile(
            thumb_io,
            None,
            thumb_filename,
            'image/jpeg',
            sys.getsizeof(thumb_io),
            None
        )
        
        return thumbnail_file
    
    def delete(self, *args, **kwargs):
        """Delete image files when model is deleted"""
        # Delete the image files from storage
        if self.image:
            self.image.delete(save=False)
        if self.thumbnail:
            self.thumbnail.delete(save=False)
        super().delete(*args, **kwargs)
