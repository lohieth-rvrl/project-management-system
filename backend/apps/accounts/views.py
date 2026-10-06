from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import User
from .permissions import IsManagerOrAdmin
from .serializers import UserSerializer


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    search_fields = ["username", "email", "first_name", "last_name"]
    filterset_fields = ["role", "is_active"]

    def get_permissions(self):
        if self.action in ("me", "list", "retrieve", "change_password"):
            return [IsAuthenticated()]
        return [IsManagerOrAdmin()]

    def get_serializer_class(self):
        return ChangePasswordSerializer if self.action == "change_password" else UserSerializer

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        if request.method == "PATCH":  # a person may change only their own email preference here
            if "email_notifications" in request.data:
                request.user.email_notifications = bool(request.data["email_notifications"])
                request.user.save(update_fields=["email_notifications"])
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        ser = ChangePasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(ser.validated_data["old_password"]):
            return Response({"old_password": ["Current password is incorrect"]},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(ser.validated_data["new_password"], user)
        except DjangoValidationError as e:
            return Response({"new_password": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(ser.validated_data["new_password"])
        user.save()
        return Response({"detail": "Password changed"})

    def _guard(self, target):
        """Only an admin may modify an admin account."""
        if target.role == "admin" and self.request.user.role != "admin":
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only an admin can change an admin account")

    def perform_update(self, serializer):
        self._guard(serializer.instance)
        # Nobody can lock themselves out by deactivating or demoting their own account
        if serializer.instance.pk == self.request.user.pk:
            data = serializer.validated_data
            if data.get("is_active") is False or ("role" in data and data["role"] != self.request.user.role):
                from rest_framework.exceptions import ValidationError
                raise ValidationError("You cannot deactivate or change the role of your own account")
        serializer.save()

    def perform_destroy(self, instance):
        from rest_framework.exceptions import ValidationError
        self._guard(instance)
        if instance.pk == self.request.user.pk:
            raise ValidationError("You cannot delete your own account")
        instance.delete()
