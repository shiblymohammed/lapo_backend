"""
Cloudinary utility functions for image transformations and URL generation
"""
import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.conf import settings


class CloudinaryHelper:
    """Helper class for Cloudinary operations"""
    
    @staticmethod
    def get_optimized_url(public_id, width=None, height=None, crop='fill', quality='auto', format='auto'):
        """
        Get optimized image URL with transformations
        
        Args:
            public_id: Cloudinary public ID
            width: Target width
            height: Target height
            crop: Crop mode (fill, fit, scale, etc.)
            quality: Quality (auto, best, good, eco, low)
            format: Format (auto, jpg, png, webp, avif)
        
        Returns:
            Optimized image URL
        """
        transformation = {
            'quality': quality,
            'fetch_format': format,
        }
        
        if width:
            transformation['width'] = width
        if height:
            transformation['height'] = height
        if crop:
            transformation['crop'] = crop
        
        return cloudinary.CloudinaryImage(public_id).build_url(**transformation)
    
    @staticmethod
    def get_thumbnail_url(public_id, size=300):
        """
        Get thumbnail URL
        
        Args:
            public_id: Cloudinary public ID
            size: Thumbnail size (default 300x300)
        
        Returns:
            Thumbnail URL
        """
        return cloudinary.CloudinaryImage(public_id).build_url(
            width=size,
            height=size,
            crop='fill',
            quality='auto',
            fetch_format='auto',
            gravity='auto'  # Smart crop focusing on important parts
        )
    
    @staticmethod
    def get_responsive_srcset(public_id, widths=[640, 768, 1024, 1280, 1920]):
        """
        Generate responsive image srcset
        
        Args:
            public_id: Cloudinary public ID
            widths: List of widths for responsive images
        
        Returns:
            Dictionary with srcset and sizes
        """
        srcset = []
        for width in widths:
            url = cloudinary.CloudinaryImage(public_id).build_url(
                width=width,
                crop='scale',
                quality='auto',
                fetch_format='auto'
            )
            srcset.append(f"{url} {width}w")
        
        return {
            'srcset': ', '.join(srcset),
            'sizes': '(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw'
        }
    
    @staticmethod
    def upload_image(file, folder='uploads', public_id=None, tags=None):
        """
        Upload image to Cloudinary
        
        Args:
            file: File object or path
            folder: Cloudinary folder
            public_id: Custom public ID (optional)
            tags: List of tags (optional)
        
        Returns:
            Upload result with URL and public_id
        """
        upload_options = {
            'folder': folder,
            'quality': 'auto',
            'fetch_format': 'auto',
        }
        
        if public_id:
            upload_options['public_id'] = public_id
        if tags:
            upload_options['tags'] = tags
        
        result = cloudinary.uploader.upload(file, **upload_options)
        return result
    
    @staticmethod
    def delete_image(public_id):
        """
        Delete image from Cloudinary
        
        Args:
            public_id: Cloudinary public ID
        
        Returns:
            Deletion result
        """
        return cloudinary.uploader.destroy(public_id)
    
    @staticmethod
    def get_image_info(public_id):
        """
        Get image information from Cloudinary
        
        Args:
            public_id: Cloudinary public ID
        
        Returns:
            Image information (width, height, format, etc.)
        """
        return cloudinary.api.resource(public_id)
    
    @staticmethod
    def generate_signed_url(public_id, expiration=3600):
        """
        Generate signed URL for private images
        
        Args:
            public_id: Cloudinary public ID
            expiration: URL expiration in seconds (default 1 hour)
        
        Returns:
            Signed URL
        """
        import time
        timestamp = int(time.time()) + expiration
        
        return cloudinary.CloudinaryImage(public_id).build_url(
            sign_url=True,
            type='authenticated',
            expires_at=timestamp
        )
    
    @staticmethod
    def get_video_thumbnail(public_id, time_offset='auto'):
        """
        Get video thumbnail (for future video support)
        
        Args:
            public_id: Cloudinary public ID
            time_offset: Time offset for thumbnail (default 'auto')
        
        Returns:
            Video thumbnail URL
        """
        return cloudinary.CloudinaryVideo(public_id).build_url(
            resource_type='video',
            format='jpg',
            start_offset=time_offset
        )
    
    @staticmethod
    def apply_transformation(public_id, transformations):
        """
        Apply custom transformations to image
        
        Args:
            public_id: Cloudinary public ID
            transformations: Dictionary of transformations
        
        Returns:
            Transformed image URL
        """
        return cloudinary.CloudinaryImage(public_id).build_url(**transformations)
    
    @staticmethod
    def get_blur_placeholder(public_id):
        """
        Get blurred placeholder for lazy loading
        
        Args:
            public_id: Cloudinary public ID
        
        Returns:
            Blurred placeholder URL
        """
        return cloudinary.CloudinaryImage(public_id).build_url(
            width=100,
            quality=1,
            effect='blur:1000',
            fetch_format='auto'
        )
