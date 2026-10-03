from django.db.models import Count, Q
from rest_framework import viewsets

from apps.accounts.permissions import RolePermission

from .models import Milestone, Project, ProjectMember
from .serializers import MilestoneSerializer, ProjectMemberSerializer, ProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [RolePermission]
    search_fields = ["code", "name", "description"]
    filterset_fields = ["status", "health", "owner"]
    ordering_fields = ["created_at", "end_date", "budget", "name"]

    def get_queryset(self):
        return Project.objects.select_related("owner").annotate(
            task_count=Count("tasks", distinct=True),
            done_count=Count("tasks", filter=Q(tasks__status="done"), distinct=True),
        ).order_by("-created_at", "-id")


class ProjectMemberViewSet(viewsets.ModelViewSet):
    queryset = ProjectMember.objects.select_related("user")
    serializer_class = ProjectMemberSerializer
    permission_classes = [RolePermission]
    filterset_fields = ["project", "user"]


class MilestoneViewSet(viewsets.ModelViewSet):
    queryset = Milestone.objects.all()
    serializer_class = MilestoneSerializer
    permission_classes = [RolePermission]
    filterset_fields = ["project", "status"]
