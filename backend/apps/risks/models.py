from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords


class Risk(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MITIGATING = "mitigating", "Mitigating"
        CLOSED = "closed", "Closed"
        OCCURRED = "occurred", "Occurred"

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE,
                                related_name="risks")
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    probability = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    impact = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    score = models.PositiveSmallIntegerField(default=9, editable=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    mitigation = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-score", "-created_at"]

    @property
    def severity(self):
        if self.score >= 15:
            return "critical"
        if self.score >= 10:
            return "high"
        if self.score >= 5:
            return "medium"
        return "low"

    def save(self, *args, **kwargs):
        self.score = self.probability * self.impact
        super().save(*args, **kwargs)
