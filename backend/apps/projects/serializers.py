from rest_framework import serializers

from .models import Milestone, Project, ProjectMember


class MilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Milestone
        fields = "__all__"


class ProjectMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ProjectMember
        fields = ["id", "project", "user", "username", "role", "allocation_percent"]


class ProjectSerializer(serializers.ModelSerializer):
    task_count = serializers.IntegerField(read_only=True)
    done_count = serializers.IntegerField(read_only=True)
    owner_name = serializers.CharField(source="owner.username", read_only=True, default=None)

    class Meta:
        model = Project
        fields = [
            "id", "code", "name", "description", "status", "health", "start_date",
            "end_date", "budget", "hourly_rate", "owner", "owner_name",
            "workflow_transitions", "done_requires_approval", "task_count", "done_count", "created_at", "updated_at",
        ]

    def validate_workflow_transitions(self, value):
        if value is None:
            return value
        valid = {"todo", "in_progress", "review", "blocked", "done"}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Must be an object like {\"todo\": [\"in_progress\"]}")
        for src, targets in value.items():
            if src not in valid or not isinstance(targets, list) or any(t not in valid for t in targets):
                raise serializers.ValidationError(f"Invalid status in rule for '{src}'")
        return {src: sorted(set(t for t in targets if t != src)) for src, targets in value.items()}

    def validate(self, data):
        request = self.context.get("request")
        changing = {"workflow_transitions", "done_requires_approval"} & set(data)
        if changing and request and request.user.role not in ("admin", "manager"):
            raise serializers.ValidationError("Only a manager or admin can change workflow rules")
        start, end = data.get("start_date"), data.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError("end_date cannot be before start_date")
        return data
