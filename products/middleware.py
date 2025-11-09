"""Middleware for file upload security and validation"""
from django.core.exceptions import ValidationError
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


class FileUploadSecurityMiddleware:
    """
    Middleware to enforce file upload security policies across all requests.
    Validates file uploads before they reach view handlers.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Define maximum file sizes by content type (in MB)
        self.max_file_sizes = {
            'image/jpeg': 5,
            'image/png': 5,
            'image/gif': 5,
            'application/pdf': 20,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 20,
            'application/msword': 20,
        }
        
        # Define allowed content types
        self.allowed_content_types = list(self.max_file_sizes.keys())
    
    def __call__(self, request):
        # Check if request contains file uploads
        if request.method in ['POST', 'PUT', 'PATCH'] and request.FILES:
            try:
                self.validate_uploaded_files(request)
            except ValidationError as e:
                logger.warning(f"File upload validation failed: {str(e)}")
                return JsonResponse({
                    'error': 'File validation failed',
                    'details': str(e)
                }, status=400)
            except Exception as e:
                logger.error(f"Unexpected error in file upload validation: {str(e)}")
                return JsonResponse({
                    'error': 'File upload error',
                    'details': 'An unexpected error occurred during file validation'
                }, status=500)
        
        response = self.get_response(request)
        return response
    
    def validate_uploaded_files(self, request):
        """Validate all uploaded files in the request"""
        for field_name, uploaded_file in request.FILES.items():
            # Check file size
            content_type = uploaded_file.content_type
            max_size_mb = self.max_file_sizes.get(content_type)
            
            if max_size_mb is None:
                # Check if it's an allowed type
                if content_type not in self.allowed_content_types:
                    raise ValidationError(
                        f'File type not allowed: {content_type}. '
                        f'Allowed types: {", ".join(self.allowed_content_types)}'
                    )
            
            # Validate file size
            max_size_bytes = max_size_mb * 1024 * 1024
            if uploaded_file.size > max_size_bytes:
                raise ValidationError(
                    f'File "{uploaded_file.name}" exceeds maximum size of {max_size_mb}MB. '
                    f'Current size: {uploaded_file.size / (1024 * 1024):.2f}MB'
                )
            
            # Check for empty files
            if uploaded_file.size == 0:
                raise ValidationError(f'File "{uploaded_file.name}" is empty')
            
            # Validate file name (prevent path traversal)
            if '..' in uploaded_file.name or '/' in uploaded_file.name or '\\' in uploaded_file.name:
                raise ValidationError(f'Invalid file name: {uploaded_file.name}')
            
            # Log file upload attempt
            logger.info(
                f"File upload validated: {uploaded_file.name} "
                f"({uploaded_file.size} bytes, {content_type})"
            )


class FileUploadRateLimitMiddleware:
    """
    Middleware to rate limit file uploads per user/IP.
    Prevents abuse and DoS attacks through file uploads.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.upload_tracking = {}  # In production, use Redis or database
        self.max_uploads_per_minute = 10
        self.max_total_size_per_minute_mb = 50
    
    def __call__(self, request):
        # Check if request contains file uploads
        if request.method in ['POST', 'PUT', 'PATCH'] and request.FILES:
            # Get identifier (user ID or IP address)
            identifier = self.get_identifier(request)
            
            # Check rate limits
            if not self.check_rate_limit(identifier, request):
                logger.warning(f"Rate limit exceeded for {identifier}")
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'details': 'Too many file uploads. Please try again later.'
                }, status=429)
        
        response = self.get_response(request)
        return response
    
    def get_identifier(self, request):
        """Get unique identifier for rate limiting"""
        if request.user.is_authenticated:
            return f"user_{request.user.id}"
        else:
            # Use IP address for anonymous users
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            return f"ip_{ip}"
    
    def check_rate_limit(self, identifier, request):
        """
        Check if user/IP has exceeded rate limits.
        In production, implement with Redis for distributed systems.
        """
        # This is a simplified implementation
        # In production, use Redis with sliding window or token bucket algorithm
        
        import time
        current_time = time.time()
        
        # Clean old entries (older than 1 minute)
        if identifier in self.upload_tracking:
            self.upload_tracking[identifier] = [
                (timestamp, size) for timestamp, size in self.upload_tracking[identifier]
                if current_time - timestamp < 60
            ]
        else:
            self.upload_tracking[identifier] = []
        
        # Calculate current usage
        upload_count = len(self.upload_tracking[identifier])
        total_size = sum(size for _, size in self.upload_tracking[identifier])
        
        # Calculate new upload size
        new_upload_size = sum(f.size for f in request.FILES.values())
        
        # Check limits
        if upload_count >= self.max_uploads_per_minute:
            return False
        
        if (total_size + new_upload_size) > (self.max_total_size_per_minute_mb * 1024 * 1024):
            return False
        
        # Add current upload to tracking
        self.upload_tracking[identifier].append((current_time, new_upload_size))
        
        return True
