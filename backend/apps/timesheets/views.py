from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.permissions import RolePermission

from .models import TimeEntry
from .serializers import TimeEntrySerializer


class TimeEntryViewSet(viewsets.ModelViewSet):
    serializer_class = TimeEntrySerializer
    permission_classes = [RolePermission]
    filterset_fields = ["task", "user", "approved", "work_date", "task__project"]
    ordering_fields = ["work_date", "hours"]

    def get_queryset(self):
        qs = TimeEntry.objects.select_related("task", "user")
        user = self.request.user
        # Managers/admins/leads see everyone; members and viewers see their own
        if user.role in ("admin", "manager", "lead"):
            return qs
        return qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.approved:
            raise PermissionDenied("Approved entries cannot be edited")
        serializer.save()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if request.user.role not in ("admin", "manager", "lead"):
            raise PermissionDenied("Only leads and managers can approve time")
        entry = self.get_object()
        entry.approved = True
        entry.approved_by = request.user
        entry.save()
        return Response(TimeEntrySerializer(entry).data)
