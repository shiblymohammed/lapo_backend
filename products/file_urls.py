"""URL patterns for secure file serving"""
from django.urls import path
from products.file_views import (
    serve_product_image,
    serve_dynamic_resource,
    serve_order_resource,
)

urlpatterns = [
    path('images/<int:image_id>/', serve_product_image, name='serve_product_image'),
    path('resources/<int:submission_id>/', serve_dynamic_resource, name='serve_dynamic_resource'),
    path('orders/<int:order_id>/<str:resource_type>/', serve_order_resource, name='serve_order_resource'),
]
