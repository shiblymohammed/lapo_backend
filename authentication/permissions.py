from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Permission class to check if user has admin role.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )


class IsStaff(permissions.BasePermission):
    """
    Permission class to check if user has staff role.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['staff', 'admin']
        )


class IsAdminOrStaff(permissions.BasePermission):
    """
    Permission class to check if user has admin or staff role.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'staff']
        )


class IsAuthenticatedUser(permissions.BasePermission):
    """
    Permission class to check if user is authenticated.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
