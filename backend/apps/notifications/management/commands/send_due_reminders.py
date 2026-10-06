"""Remind assignees about tasks that are due within two days or already overdue.

    python manage.py send_due_reminders

Run it once a day from any scheduler (cron, Render cron job, GitHub Actions schedule).
Safe to run more often: each person gets at most one reminder per task per day.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.tasks.models import Task


class Command(BaseCommand):
    help = "Create 'due soon / overdue' notifications for assigned, unfinished tasks"

    def handle(self, *args, **opts):
        today = timezone.localdate()
        soon = today + timedelta(days=2)
        tasks = (Task.objects.filter(due_date__lte=soon, assignee__isnull=False)
                 .exclude(status="done").select_related("assignee", "project"))
        sent = 0
        for t in tasks:
            link = f"/tasks?task={t.id}"
            already = Notification.objects.filter(
                user=t.assignee, kind=Notification.Kind.DUE, link=link, created_at__date=today).exists()
            if already:
                continue
            late = (today - t.due_date).days
            when = f"overdue by {late} day(s)" if late > 0 else ("due today" if late == 0 else f"due on {t.due_date}")
            notify([t.assignee], Notification.Kind.DUE, f"{t.title} is {when}",
                   f"{t.project.code} task assigned to you.", link)
            sent += 1
        self.stdout.write(self.style.SUCCESS(f"{sent} reminder(s) created"))
