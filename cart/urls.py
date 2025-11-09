from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_cart, name='get-cart'),
    path('add/', views.add_to_cart, name='add-to-cart'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove-from-cart'),
    path('clear/', views.clear_cart, name='clear-cart'),
]
