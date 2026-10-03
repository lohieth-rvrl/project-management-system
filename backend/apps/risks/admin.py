from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Risk


@admin.register(Risk)
class RiskAdmin(SimpleHistoryAdmin):
    list_display = ("title", "project", "score", "status", "owner")
    list_filter = ("status", "project")
