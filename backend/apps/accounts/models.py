from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    MANAGER = "manager", "Manager"
    LEAD = "lead", "Team Lead"
    MEMBER = "member", "Member"
    VIEWER = "viewer", "Viewer"


class User(AbstractUser):
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    weekly_capacity_hours = models.DecimalField(max_digits=5, decimal_places=2, default=40)
    email_notifications = models.BooleanField(default=True)
    history = HistoricalRecords()

    @property
    def can_write(self):
        return self.role != Role.VIEWER

    @property
    def is_manager_or_above(self):
        return self.role in (Role.ADMIN, Role.MANAGER)

    def __str__(self):
        return self.get_full_name() or self.username
