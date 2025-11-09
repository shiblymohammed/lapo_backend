"""
URL configuration for election_cart project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import connection
from django.utils import timezone
import logging

from admin_panel.views import StaffOrderListView, StaffOrderDetailView, update_checklist_item

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Health check endpoint for monitoring system status.
    
    Returns:
        - 200 OK: System is healthy (database connected)
        - 503 Service Unavailable: System is unhealthy (database disconnected)
    
    Response format:
        {
            "status": "healthy" | "unhealthy",
            "service": "election-cart-api",
            "database": "connected" | "disconnected",
            "memory_mb": 150.25,
            "memory_warning": false,
            "timestamp": "2025-11-03T14:23:45Z"
        }
    """
    try:
        # Import psutil at function level to avoid dependency issues
        import psutil
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        # Calculate current memory usage
        process = psutil.Process()
        mem_info = process.memory_info()
        
        # Convert RSS memory to megabytes
        memory_mb = mem_info.rss / 1024 / 1024
        
        # Calculate total memory across all worker processes
        parent = process.parent()
        total_memory_mb = memory_mb
        
        if parent:
            try:
                # Get memory from all child processes (workers)
                children = parent.children(recursive=True)
                for child in children:
                    try:
                        child_mem = child.memory_info().rss / 1024 / 1024
                        total_memory_mb += child_mem
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # If we can't access parent, just use current process memory
                total_memory_mb = memory_mb
        
        # Check if memory exceeds 400MB threshold
        memory_warning = total_memory_mb > 400
        
        response_data = {
            'status': 'healthy',
            'service': 'election-cart-api',
            'database': 'connected',
            'memory_mb': round(total_memory_mb, 2),
            'memory_warning': memory_warning,
            'timestamp': timezone.now().isoformat()
        }
        
        if memory_warning:
            logger.warning(f"Health check - memory warning: {total_memory_mb:.2f}MB exceeds 400MB threshold")
        else:
            logger.info(f"Health check passed - system healthy, memory: {total_memory_mb:.2f}MB")
        
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        response_data = {
            'status': 'unhealthy',
            'service': 'election-cart-api',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }
        
        logger.error(f"Health check failed - database error: {e}", exc_info=True)
        return JsonResponse(response_data, status=503)


urlpatterns = [
    # Health check endpoint (no authentication required)
    path('health/', health_check, name='health-check'),
    
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/', include('products.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/admin/', include('admin_panel.urls')),
    # Staff endpoints
    path('api/staff/orders/', StaffOrderListView.as_view(), name='staff-order-list'),
    path('api/staff/orders/<int:pk>/', StaffOrderDetailView.as_view(), name='staff-order-detail'),
    path('api/staff/checklist/<int:item_id>/', update_checklist_item, name='staff-checklist-update'),
    # Secure file serving
    path('api/secure-files/', include('products.file_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
