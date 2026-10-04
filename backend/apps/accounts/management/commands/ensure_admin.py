"""Create (or update) the first admin from environment variables.

Safe to run on every deploy: python manage.py ensure_admin
Needs DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD; email is optional.
If either required variable is missing it does nothing.
"""
import os

from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create the admin user from DJANGO_SUPERUSER_* environment variables"

    def handle(self, *args, **opts):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        if not username or not password:
            self.stdout.write("DJANGO_SUPERUSER_USERNAME/PASSWORD not set: skipping admin setup")
            return
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})
        user.role = "admin"
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        if email:
            user.email = email
        if created or not user.check_password(password):
            user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Admin '{username}' {'created' if created else 'updated'}"))
