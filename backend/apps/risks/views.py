from rest_framework import viewsets

from apps.accounts.permissions import RolePermission

from .models import Risk
from .serializers import RiskSerializer


class RiskViewSet(viewsets.ModelViewSet):
    queryset = Risk.objects.all()
    serializer_class = RiskSerializer
    permission_classes = [RolePermission]
    search_fields = ["title", "description"]
    filterset_fields = ["project", "status", "owner"]
    ordering_fields = ["score", "created_at"]
