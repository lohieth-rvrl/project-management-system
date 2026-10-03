from rest_framework import serializers

from .models import Risk


class RiskSerializer(serializers.ModelSerializer):
    severity = serializers.CharField(read_only=True)

    class Meta:
        model = Risk
        fields = ["id", "project", "title", "description", "probability", "impact", "score",
                  "severity", "status", "mitigation", "owner", "created_at"]
        read_only_fields = ["score"]
