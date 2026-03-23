from rest_framework import permissions

class IsManagerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow managers and admins to access a view.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['manager', 'admin']
