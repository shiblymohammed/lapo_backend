from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('me/', views.get_user_profile, name='user-profile'),
    
    # User management endpoints (Admin only)
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/create/', views.create_user, name='user-create'),
    path('users/<int:user_id>/role/', views.update_user_role, name='user-update-role'),
    path('users/<int:user_id>/', views.delete_user, name='user-delete'),
]
