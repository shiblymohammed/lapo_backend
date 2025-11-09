from django.core.cache import cache
from functools import wraps
import hashlib
import json


def cache_analytics(timeout=300):
    """
    Decorator to cache analytics API responses.
    
    Args:
        timeout: Cache timeout in seconds (default 300 = 5 minutes)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Generate cache key based on view name and query parameters
            query_params = dict(request.query_params)
            cache_key_data = {
                'view': view_func.__name__,
                'params': query_params,
                'args': args,
                'kwargs': kwargs
            }
            
            # Create a hash of the cache key data
            cache_key_str = json.dumps(cache_key_data, sort_keys=True)
            cache_key_hash = hashlib.md5(cache_key_str.encode()).hexdigest()
            cache_key = f'analytics:{view_func.__name__}:{cache_key_hash}'
            
            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return cached_response
            
            # Call the view function
            response = view_func(request, *args, **kwargs)
            
            # Cache the response if successful
            if response.status_code == 200:
                # Render the response before caching to avoid pickle errors
                response.render()
                cache.set(cache_key, response, timeout)
            
            return response
        
        return wrapper
    return decorator


def invalidate_analytics_cache():
    """
    Invalidate all analytics cache entries.
    This should be called when new orders are created or updated.
    """
    # Get all cache keys (this is implementation-specific)
    # For LocMemCache, we can use cache.clear() to clear all
    # For Redis, we would use pattern matching
    
    # Simple approach: clear all cache
    # In production with Redis, you could use:
    # cache.delete_pattern('analytics:*')
    
    cache.clear()
    return True


def get_cache_key_for_analytics(view_name, **params):
    """
    Generate a cache key for analytics data.
    
    Args:
        view_name: Name of the analytics view
        **params: Query parameters
        
    Returns:
        str: Cache key
    """
    cache_key_data = {
        'view': view_name,
        'params': params
    }
    cache_key_str = json.dumps(cache_key_data, sort_keys=True)
    cache_key_hash = hashlib.md5(cache_key_str.encode()).hexdigest()
    return f'analytics:{view_name}:{cache_key_hash}'
