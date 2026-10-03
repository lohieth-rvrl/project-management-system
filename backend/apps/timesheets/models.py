from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class TimeEntry(models.Model):
    task = models.ForeignKey("tasks.Task", on_delete=models.CASCADE,
                             related_name="time_entries")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="time_entries")
    work_date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    note = models.CharField(max_length=300, blank=True)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-work_date", "-id"]
        verbose_name_plural = "time entries"
