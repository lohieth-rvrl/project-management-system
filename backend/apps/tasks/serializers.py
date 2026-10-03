from rest_framework import serializers

from .models import Comment, Sprint, Task, TaskDependency


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
        return data


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
