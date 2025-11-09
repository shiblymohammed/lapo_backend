from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'packages', views.PackageViewSet, basename='package')
router.register(r'campaigns', views.CampaignViewSet, basename='campaign')

urlpatterns = [
    path('', include(router.urls)),
    
    # All admin product management endpoints moved to admin_panel/urls.py to avoid URL conflicts
    
    # Public product image viewing (non-admin)
    path('products/<str:product_type>/<int:product_id>/images/', 
         views.ProductImageViewSet.as_view({
             'get': 'list'
         }), 
         name='product-images-list'),
]
