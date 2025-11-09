"""
Celery tasks for product image processing
"""
from celery import shared_task
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import os
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_thumbnail_async(self, product_image_id):
    """
    Generate thumbnail for a product image asynchronously
    
    Note: When Cloudinary is enabled, thumbnail generation is skipped as Cloudinary
    handles thumbnail transformations automatically via URL parameters.
    
    Args:
        product_image_id: ID of the ProductImage to generate thumbnail for
        
    Returns:
        dict: Status and message
    """
    try:
        from .models import ProductImage
        from django.conf import settings
        
        # Skip thumbnail generation if Cloudinary is enabled
        if settings.USE_CLOUDINARY:
            logger.info(f"Skipping thumbnail generation for ProductImage {product_image_id} - Cloudinary handles transformations automatically")
            return {
                'status': 'skipped',
                'message': 'Cloudinary handles thumbnail transformations automatically'
            }
        
        # Get the product image
        product_image = ProductImage.objects.get(id=product_image_id)
        
        if not product_image.image:
            logger.error(f"No image found for ProductImage {product_image_id}")
            return {
                'status': 'error',
                'message': 'No image found'
            }
        
        # Open the image
        img = Image.open(product_image.image)
        
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
        original_name = os.path.basename(product_image.image.name)
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
        
        # Save thumbnail
        product_image.thumbnail = thumbnail_file
        product_image.save(update_fields=['thumbnail'])
        
        logger.info(f"Thumbnail generated successfully for ProductImage {product_image_id}")
        
        return {
            'status': 'success',
            'message': f'Thumbnail generated for ProductImage {product_image_id}'
        }
        
    except ProductImage.DoesNotExist:
        logger.error(f"ProductImage {product_image_id} not found")
        return {
            'status': 'error',
            'message': f'ProductImage {product_image_id} not found'
        }
    except Exception as exc:
        logger.error(f"Error generating thumbnail for ProductImage {product_image_id}: {str(exc)}")
        # Retry the task
        raise self.retry(exc=exc, countdown=60)  # Retry after 60 seconds


@shared_task(bind=True, max_retries=3)
def optimize_product_image_async(self, product_image_id):
    """
    Optimize a product image asynchronously (compress, resize if too large)
    
    Args:
        product_image_id: ID of the ProductImage to optimize
        
    Returns:
        dict: Status and message
    """
    try:
        from .models import ProductImage
        
        # Get the product image
        product_image = ProductImage.objects.get(id=product_image_id)
        
        if not product_image.image:
            logger.error(f"No image found for ProductImage {product_image_id}")
            return {
                'status': 'error',
                'message': 'No image found'
            }
        
        # Open the image
        img = Image.open(product_image.image)
        
        # Check if image is too large (> 2000px on any side)
        max_dimension = 2000
        if img.width > max_dimension or img.height > max_dimension:
            # Resize while maintaining aspect ratio
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            # Save optimized image
            img_io = BytesIO()
            img_format = img.format or 'JPEG'
            img.save(img_io, format=img_format, quality=85, optimize=True)
            img_io.seek(0)
            
            # Update the image file
            original_name = os.path.basename(product_image.image.name)
            optimized_file = InMemoryUploadedFile(
                img_io,
                None,
                original_name,
                f'image/{img_format.lower()}',
                sys.getsizeof(img_io),
                None
            )
            
            product_image.image = optimized_file
            product_image.save(update_fields=['image'])
            
            logger.info(f"Image optimized successfully for ProductImage {product_image_id}")
            
            return {
                'status': 'success',
                'message': f'Image optimized for ProductImage {product_image_id}'
            }
        else:
            logger.info(f"Image already optimal for ProductImage {product_image_id}")
            return {
                'status': 'success',
                'message': f'Image already optimal for ProductImage {product_image_id}'
            }
        
    except ProductImage.DoesNotExist:
        logger.error(f"ProductImage {product_image_id} not found")
        return {
            'status': 'error',
            'message': f'ProductImage {product_image_id} not found'
        }
    except Exception as exc:
        logger.error(f"Error optimizing image for ProductImage {product_image_id}: {str(exc)}")
        # Retry the task
        raise self.retry(exc=exc, countdown=60)  # Retry after 60 seconds
