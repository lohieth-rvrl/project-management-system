"""Create the app's Postgres schema if DB_SCHEMA is set: python manage.py ensure_schema

Run before `migrate` on every start. Does nothing on SQLite or when DB_SCHEMA is unset.
"""
import os

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "CREATE SCHEMA IF NOT EXISTS for DB_SCHEMA (Postgres only)"

    def handle(self, *args, **opts):
        schema = os.environ.get("DB_SCHEMA", "").strip()
        if not schema or connection.vendor != "postgresql":
            self.stdout.write("No DB_SCHEMA / not Postgres: nothing to do")
            return
        with connection.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {connection.ops.quote_name(schema)}")
        self.stdout.write(self.style.SUCCESS(f"Schema '{schema}' is ready"))
