from rest_framework import viewsets

from apps.accounts.permissions import RolePermission
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Risk
from .serializers import RiskSerializer


class RiskViewSet(viewsets.ModelViewSet):
    queryset = Risk.objects.all()
    serializer_class = RiskSerializer
    permission_classes = [RolePermission]
    search_fields = ["title", "description"]
    filterset_fields = ["project", "status", "owner"]
    ordering_fields = ["score", "created_at"]

    def perform_create(self, serializer):
        risk = serializer.save()
        if risk.score >= 15:  # critical: tell the project owner and the risk owner, and post to Slack/Teams
            notify([risk.project.owner, risk.owner], Notification.Kind.RISK,
                   f"Critical risk on {risk.project.code}: {risk.title}",
                   f"Probability {risk.probability} x impact {risk.impact} = {risk.score}",
                   "/risks", actor=self.request.user, webhook=True)
