"""Create (or update) the first admin from environment variables.

Safe to run on every deploy: python manage.py ensure_admin
Needs DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD; email is optional.
If either required variable is missing it does nothing.
The password is only applied on creation (or with DJANGO_SUPERUSER_FORCE_PASSWORD=1).
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
        # The env password is used only when the admin is first created, so a password changed in
        # the app survives redeploys. To force a reset, set DJANGO_SUPERUSER_FORCE_PASSWORD=1 for one deploy.
        if created or os.environ.get("DJANGO_SUPERUSER_FORCE_PASSWORD") == "1":
            user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Admin '{username}' {'created' if created else 'updated'}"))
        # Optional example data (only when SEED_SHOWCASE=1); runs here because this command is
        # already part of the start-up sequence on every deploy.
        from django.core.management import call_command
        call_command("seed_showcase")
