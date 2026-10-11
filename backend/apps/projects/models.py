from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class Project(models.Model):
    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Health(models.TextChoices):
        GREEN = "green", "On Track"
        AMBER = "amber", "At Risk"
        RED = "red", "Off Track"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PLANNING)
    health = models.CharField(max_length=6, choices=Health.choices, default=Health.GREEN)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                      help_text="Cost per logged hour, used for cost vs budget")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="owned_projects")
    # Workflow rules. null = any status change is allowed. Otherwise a map such as
    # {"todo": ["in_progress"], "in_progress": ["review", "blocked"]}; a status that is
    # missing from the map is unrestricted, and [] means "no moves out of this status".
    workflow_transitions = models.JSONField(null=True, blank=True, default=None)
    done_requires_approval = models.BooleanField(
        default=False, help_text="Only a lead, manager or admin may move a task to Done")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class ProjectMember(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="memberships")
    role = models.CharField(max_length=50, default="Contributor")
    allocation_percent = models.PositiveSmallIntegerField(default=100)
    history = HistoricalRecords()

    class Meta:
        unique_together = ("project", "user")


class Milestone(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DONE = "done", "Done"
        MISSED = "missed", "Missed"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
    name = models.CharField(max_length=200)
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    history = HistoricalRecords()

    class Meta:
        ordering = ["due_date"]
