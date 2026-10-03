from rest_framework import serializers

from .models import TimeEntry


class TimeEntrySerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source="task.title", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    project = serializers.IntegerField(source="task.project_id", read_only=True)

    class Meta:
        model = TimeEntry
        fields = ["id", "task", "task_title", "project", "user", "username", "work_date",
                  "hours", "note", "approved", "approved_by", "created_at"]
        read_only_fields = ["user", "approved", "approved_by"]

    def validate_hours(self, value):
        if value <= 0 or value > 24:
            raise serializers.ValidationError("Hours must be between 0 and 24")
        return value
