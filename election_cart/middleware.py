"""
Custom middleware for handling rate limiting and other cross-cutting concerns
"""

from django.http import JsonResponse
from django_ratelimit.exceptions import Ratelimited
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """
    Middleware to handle rate limit exceptions and return proper 429 responses
    """
    
    def process_exception(self, request, exception):
        """
        Handle Ratelimited exceptions and return 429 response
        """
        if isinstance(exception, Ratelimited):
            logger.warning(
                f"Rate limit exceeded for {request.path} from IP: {request.META.get('REMOTE_ADDR')} "
                f"User: {request.user.id if request.user.is_authenticated else 'Anonymous'}"
            )
            
            return JsonResponse({
                'error': 'Too many requests. Please try again later.',
                'detail': 'Rate limit exceeded'
            }, status=429)
        
        return None
