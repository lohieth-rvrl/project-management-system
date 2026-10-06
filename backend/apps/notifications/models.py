from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        ASSIGNED = "assigned", "Assigned to you"
        COMMENT = "comment", "New comment"
        STATUS = "status", "Status changed"
        MENTION = "mention", "You were mentioned"
        APPROVED = "approved", "Time approved"
        RISK = "risk", "Critical risk"
        DUE = "due", "Due soon or overdue"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="+")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=200, blank=True, help_text="In-app path, e.g. /tasks?task=12")
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "read_at"])]

    def __str__(self):
        return f"{self.user} - {self.title}"
