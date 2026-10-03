from rest_framework.permissions import SAFE_METHODS, BasePermission


class RolePermission(BasePermission):
    """Read: any authenticated user. Write: everyone except viewers.
    Delete: manager or admin only."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return user.is_manager_or_above
        return user.can_write


class IsManagerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_manager_or_above)
