import django_filters
from django.utils import timezone
from rest_framework import viewsets

from apps.accounts.permissions import RolePermission
from apps.notifications.models import Notification
from apps.notifications.services import find_mentions, notify

from .models import Comment, Sprint, Task, TaskDependency
from .serializers import (CommentSerializer, SprintSerializer, TaskDependencySerializer,
                          TaskSerializer)


class TaskFilter(django_filters.FilterSet):
    overdue = django_filters.BooleanFilter(method="filter_overdue")
    unassigned = django_filters.BooleanFilter(method="filter_unassigned")
    due_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
    due_after = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")

    class Meta:
        model = Task
        fields = ["project", "sprint", "status", "priority", "assignee", "parent"]

    def filter_overdue(self, qs, name, value):
        late = qs.filter(due_date__lt=timezone.localdate()).exclude(status="done")
        return late if value else qs.exclude(pk__in=late.values("pk"))

    def filter_unassigned(self, qs, name, value):
        return qs.filter(assignee__isnull=bool(value))


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related("assignee", "project")
    serializer_class = TaskSerializer
    permission_classes = [RolePermission]
    search_fields = ["title", "description"]
    filterset_class = TaskFilter
    ordering_fields = ["created_at", "due_date", "priority", "updated_at"]

    def perform_create(self, serializer):
        status = serializer.validated_data.get("status")
        extra = {"reporter": self.request.user}
        if status == Task.Status.DONE:
            extra["completed_at"] = timezone.now()
        task = serializer.save(**extra)
        if task.assignee_id:
            self._notify_assigned(task)

    def perform_update(self, serializer):
        new_status = serializer.validated_data.get("status")
        old_status, old_assignee = serializer.instance.status, serializer.instance.assignee_id
        extra = {}
        if new_status == Task.Status.DONE and old_status != Task.Status.DONE:
            extra["completed_at"] = timezone.now()
        elif new_status and new_status != Task.Status.DONE:
            extra["completed_at"] = None
        task = serializer.save(**extra)
        if task.assignee_id and task.assignee_id != old_assignee:
            self._notify_assigned(task)
        if task.status != old_status:
            labels = dict(Task.Status.choices)
            notify([task.assignee, task.reporter], Notification.Kind.STATUS,
                   f"{task.title}: {labels.get(old_status, old_status)} to {labels.get(task.status, task.status)}",
                   f"{task.project.code}", f"/tasks?task={task.id}", actor=self.request.user,
                   webhook=task.status == Task.Status.BLOCKED)

    def _notify_assigned(self, task):
        notify([task.assignee], Notification.Kind.ASSIGNED, f"You were assigned: {task.title}",
               f"{task.project.code} - {task.get_priority_display()} priority"
               + (f", due {task.due_date}" if task.due_date else ""),
               f"/tasks?task={task.id}", actor=self.request.user)


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
        comment = serializer.save(author=self.request.user)
        task, actor = comment.task, self.request.user
        who = actor.get_full_name() or actor.username
        link = f"/tasks?task={task.id}"
        mentioned = find_mentions(comment.body)
        notify(mentioned, Notification.Kind.MENTION, f"{who} mentioned you on: {task.title}",
               comment.body[:300], link, actor=actor)
        mentioned_ids = {u.pk for u in mentioned}
        others = [u for u in (task.assignee, task.reporter) if u and u.pk not in mentioned_ids]
        notify(others, Notification.Kind.COMMENT, f"{who} commented on: {task.title}",
               comment.body[:300], link, actor=actor)
