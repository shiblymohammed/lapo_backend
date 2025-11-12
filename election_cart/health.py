"""
Health check endpoint for monitoring and keeping the service warm
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import time

start_time = time.time()

@csrf_exempt
@require_http_methods(["GET", "HEAD"])
def health_check(request):
    """
    Simple health check endpoint that returns 200 OK
    Used for:
    - Monitoring service availability
    - Keeping Render free tier warm
    - Load balancer health checks
    """
    uptime = int(time.time() - start_time)
    
    return JsonResponse({
        'status': 'healthy',
        'uptime_seconds': uptime,
        'service': 'electioncart-backend'
    }, status=200)


@csrf_exempt
@require_http_methods(["GET"])
def warmup(request):
    """
    Warmup endpoint to prepare the service
    Can be called periodically to prevent cold starts
    """
    return JsonResponse({
        'status': 'warm',
        'message': 'Service is ready'
    }, status=200)
