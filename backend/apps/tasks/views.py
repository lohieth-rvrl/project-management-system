from django.utils import timezone
from rest_framework import viewsets

from apps.accounts.permissions import RolePermission

from .models import Comment, Sprint, Task, TaskDependency
from .serializers import (CommentSerializer, SprintSerializer, TaskDependencySerializer,
                          TaskSerializer)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related("assignee", "project")
    serializer_class = TaskSerializer
    permission_classes = [RolePermission]
    search_fields = ["title", "description"]
    filterset_fields = ["project", "sprint", "status", "priority", "assignee", "parent"]
    ordering_fields = ["created_at", "due_date", "priority", "updated_at"]

    def perform_create(self, serializer):
        status = serializer.validated_data.get("status")
        extra = {"reporter": self.request.user}
        if status == Task.Status.DONE:
            extra["completed_at"] = timezone.now()
        serializer.save(**extra)

    def perform_update(self, serializer):
        new_status = serializer.validated_data.get("status")
        extra = {}
        if new_status == Task.Status.DONE and serializer.instance.status != Task.Status.DONE:
            extra["completed_at"] = timezone.now()
        elif new_status and new_status != Task.Status.DONE:
            extra["completed_at"] = None
        serializer.save(**extra)


class SprintViewSet(viewsets.ModelViewSet):
    queryset = Sprint.objects.all()
    serializer_class = SprintSerializer
    permission_classes = [RolePermission]
    filterset_fields = ["project"]


class TaskDependencyViewSet(viewsets.ModelViewSet):
    queryset = TaskDependency.objects.all()
    serializer_class = TaskDependencySerializer
    permission_classes = [RolePermission]
    filterset_fields = ["task", "depends_on"]


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.select_related("author")
    serializer_class = CommentSerializer
    permission_classes = [RolePermission]
    filterset_fields = ["task"]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
