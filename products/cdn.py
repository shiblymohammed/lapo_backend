"""
CDN integration for product images
Provides utilities to generate CDN URLs for images
"""
import os
from django.conf import settings
from urllib.parse import urljoin


class CDNService:
    """Service for handling CDN URL generation"""
    
    @staticmethod
    def get_cdn_url(file_path):
        """
        Generate CDN URL for a file path
        
        Args:
            file_path: Relative file path (e.g., 'product_images/image.jpg')
        
        Returns:
            Full CDN URL or regular media URL if CDN is not configured
        """
        if not file_path:
            return None
        
        # Get CDN base URL from settings
        cdn_base_url = getattr(settings, 'CDN_BASE_URL', None)
        
        if cdn_base_url:
            # Use CDN URL
            return urljoin(cdn_base_url, file_path)
        else:
            # Fallback to regular media URL
            media_url = settings.MEDIA_URL
            return urljoin(media_url, file_path)
    
    @staticmethod
    def get_image_url_with_cache_headers(file_path):
        """
        Generate image URL with cache-busting query parameter
        
        Args:
            file_path: Relative file path
        
        Returns:
            URL with cache headers
        """
        base_url = CDNService.get_cdn_url(file_path)
        
        if not base_url:
            return None
        
        # Add cache version parameter if configured
        cache_version = getattr(settings, 'STATIC_CACHE_VERSION', None)
        if cache_version:
            separator = '&' if '?' in base_url else '?'
            return f"{base_url}{separator}v={cache_version}"
        
        return base_url
