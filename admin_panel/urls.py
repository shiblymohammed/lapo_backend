from django.urls import path, re_path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminOrderListView,
    AdminOrderDetailView,
    get_order_statistics,
    assign_order_to_staff,
    StaffListView,
    NotificationListView,
    mark_notification_read,
    mark_all_notifications_read,
    StaffOrderListView,
    StaffOrderDetailView,
    update_checklist_item,
    manage_product_resource_fields,
    manage_resource_field,
    reorder_resource_fields,
    analytics_overview,
    analytics_revenue_trend,
    analytics_top_products,
    analytics_staff_performance,
    analytics_order_distribution,
    analytics_export,
    toggle_package_popular,
    toggle_campaign_popular,
    reorder_popular_packages,
    reorder_popular_campaigns,
    download_order_invoice,
    delete_product_image_view,
    update_customer_info,
)
# Import manual order views
from .manual_order_views import (
    create_manual_order,
    search_customers,
    get_products_for_order,
    record_payment,
    update_payment_status,
    update_order_status,
)
# Import product views for admin product management
from products import views as product_views
from products.models import ProductImage

# Create router for ProductImageViewSet
image_router = DefaultRouter()
image_router.register(r'products/images', product_views.ProductImageViewSet, basename='product-images')

urlpatterns = [
    # Order management endpoints
    path('orders/statistics/', get_order_statistics, name='admin-order-statistics'),
    path('orders/', AdminOrderListView.as_view(), name='admin-order-list'),
    path('orders/<int:pk>/', AdminOrderDetailView.as_view(), name='admin-order-detail'),
    path('orders/<int:order_id>/assign/', assign_order_to_staff, name='admin-order-assign'),
    path('orders/<int:order_id>/invoice/', download_order_invoice, name='admin-download-invoice'),
    
    # Manual order creation endpoints
    path('orders/manual/', create_manual_order, name='create-manual-order'),
    path('orders/<int:order_id>/update-status/', update_order_status, name='update-order-status'),
    path('orders/<int:order_id>/update-payment-status/', update_payment_status, name='update-payment-status'),
    path('orders/<int:order_id>/record-payment/', record_payment, name='record-payment'),
    path('customers/search/', search_customers, name='search-customers'),
    path('customers/<int:user_id>/update/', update_customer_info, name='update-customer-info'),
    path('products/for-order/', get_products_for_order, name='products-for-order'),
    
    # Staff management endpoints
    path('staff/', StaffListView.as_view(), name='admin-staff-list'),
    
    # Notification endpoints
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:notification_id>/mark-read/', mark_notification_read, name='notification-mark-read'),
    path('notifications/mark-all-read/', mark_all_notifications_read, name='notification-mark-all-read'),
    
    # Product management endpoints
    path('products/', product_views.list_all_products, name='product-list'),
    path('products/package/', product_views.create_package, name='package-create'),
    path('products/campaign/', product_views.create_campaign, name='campaign-create'),
    
    # Resource field management endpoints - MUST come before product detail to avoid conflicts
    path('products/resource-fields/reorder/', reorder_resource_fields, name='reorder-resource-fields'),
    path('products/resource-fields/<int:field_id>/', manage_resource_field, name='manage-resource-field'),
    path('products/<str:product_type>/<int:product_id>/resource-fields/', manage_product_resource_fields, name='product-resource-fields'),
    
    # Product detail and management - comes after more specific patterns
    path('products/<str:product_type>/<int:product_id>/', product_views.get_product_detail, name='product-detail'),
    path('products/<str:product_type>/<int:product_id>/update/', product_views.update_product, name='product-update'),
    path('products/<str:product_type>/<int:product_id>/delete/', product_views.delete_product, name='product-delete'),
    path('products/<str:product_type>/<int:product_id>/toggle-status/', product_views.toggle_product_status, name='product-toggle-status'),
    path('products/<str:product_type>/<int:product_id>/audit-logs/', product_views.get_product_audit_logs, name='product-audit-logs'),
    
    # Checklist template management endpoints
    path('products/<str:product_type>/<int:product_id>/checklist-template/', 
         product_views.ChecklistTemplateViewSet.as_view({
             'get': 'list',
             'post': 'create'
         }), 
         name='checklist-template-list'),
    path('products/checklist-template/<int:pk>/', 
         product_views.ChecklistTemplateViewSet.as_view({
             'get': 'retrieve',
             'put': 'update',
             'patch': 'partial_update',
             'delete': 'destroy'
         }), 
         name='checklist-template-detail'),
    path('products/checklist-template/reorder/', 
         product_views.ChecklistTemplateViewSet.as_view({
             'patch': 'reorder'
         }), 
         name='checklist-template-reorder'),
    
    # Product image management endpoints
    path('products/<str:product_type>/<int:product_id>/images/', 
         product_views.ProductImageViewSet.as_view({
             'post': 'create'
         }), 
         name='product-images-create'),
    # Test endpoint
    path('test/', product_views.test_endpoint, name='test-endpoint'),
    
    # Product image delete endpoint (simple function-based view)
    path('products/images/<int:pk>/delete/', delete_product_image_view, name='product-images-delete'),
    
    # Include router URLs for ProductImageViewSet (handles CRUD operations)
    path('', include(image_router.urls)),
    
    # Custom image endpoints that aren't part of standard CRUD
    path('products/images/reorder/', 
         product_views.ProductImageViewSet.as_view({
             'patch': 'reorder'
         }), 
         name='product-images-reorder'),
    path('products/images/<int:pk>/set-primary/', 
         product_views.ProductImageViewSet.as_view({
             'patch': 'set_primary'
         }), 
         name='product-images-set-primary'),
    

    
    # Analytics endpoints
    path('analytics/overview/', analytics_overview, name='analytics-overview'),
    path('analytics/revenue-trend/', analytics_revenue_trend, name='analytics-revenue-trend'),
    path('analytics/top-products/', analytics_top_products, name='analytics-top-products'),
    path('analytics/staff-performance/', analytics_staff_performance, name='analytics-staff-performance'),
    path('analytics/order-distribution/', analytics_order_distribution, name='analytics-order-distribution'),
    path('analytics/export/', analytics_export, name='analytics-export'),
    
    # Popular products management
    path('products/packages/<int:pk>/toggle-popular/', toggle_package_popular, name='toggle-package-popular'),
    path('products/campaigns/<int:pk>/toggle-popular/', toggle_campaign_popular, name='toggle-campaign-popular'),
    path('products/packages/reorder-popular/', reorder_popular_packages, name='reorder-popular-packages'),
    path('products/campaigns/reorder-popular/', reorder_popular_campaigns, name='reorder-popular-campaigns'),
]
