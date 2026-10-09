from rest_framework import serializers

from .models import Attachment, Comment, Sprint, Task, TaskDependency


class SprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sprint
        fields = "__all__"

    def validate(self, data):
        if data.get("end_date") and data.get("start_date") and data["end_date"] < data["start_date"]:
            raise serializers.ValidationError("end_date cannot be before start_date")
        return data


class TaskSerializer(serializers.ModelSerializer):
    assignee_name = serializers.CharField(source="assignee.username", read_only=True,
                                          default=None)
    project_code = serializers.CharField(source="project.code", read_only=True)

    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = ["completed_at", "reporter"]

    def validate(self, data):
        parent = data.get("parent")
        project = data.get("project") or getattr(self.instance, "project", None)
        if parent and project and parent.project_id != project.id:
            raise serializers.ValidationError("Subtask must belong to the same project as its parent")
        if self.instance and parent and parent.pk == self.instance.pk:
            raise serializers.ValidationError("A task cannot be its own parent")
        self._check_workflow(data)
        return data

    def _check_workflow(self, data):
        """Project workflow rules: allowed status moves, and approval for Done."""
        new = data.get("status")
        if not self.instance or not new or new == self.instance.status:
            return
        old, project = self.instance.status, self.instance.project
        rules = project.workflow_transitions
        if rules is not None and old in rules and new not in rules[old]:
            labels = dict(Task.Status.choices)
            raise serializers.ValidationError({"status": (
                f"{project.code} does not allow moving from {labels[old]} to {labels[new]}")})
        request = self.context.get("request")
        if (new == Task.Status.DONE and project.done_requires_approval and request
                and request.user.role not in ("admin", "manager", "lead")):
            raise serializers.ValidationError({"status": (
                f"{project.code} requires a lead, manager or admin to mark tasks Done")})


class TaskDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskDependency
        fields = "__all__"

    def validate(self, data):
        if data["task"] == data["depends_on"]:
            raise serializers.ValidationError("A task cannot depend on itself")
        # reject direct cycle A->B and B->A
        if TaskDependency.objects.filter(task=data["depends_on"], depends_on=data["task"]).exists():
            raise serializers.ValidationError("Circular dependency detected")
        return data


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True,
                                        default=None)

    class Meta:
        model = Comment
        fields = ["id", "task", "author", "author_name", "body", "created_at"]
        read_only_fields = ["author"]


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.username", read_only=True, default=None)

    class Meta:
        model = Attachment
        fields = ["id", "task", "file", "name", "size", "content_type", "uploaded_by", "uploaded_by_name", "created_at"]
        read_only_fields = ["name", "size", "content_type", "uploaded_by"]
        extra_kwargs = {"file": {"write_only": True}}
