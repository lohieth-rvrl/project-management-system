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
            "task_count", "done_count", "created_at", "updated_at",
        ]

    def validate(self, data):
        start, end = data.get("start_date"), data.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError("end_date cannot be before start_date")
        return data
