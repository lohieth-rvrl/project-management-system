from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Milestone, Project, ProjectMember


@admin.register(Project)
class ProjectAdmin(SimpleHistoryAdmin):
    list_display = ("code", "name", "status", "health", "owner", "end_date")
    list_filter = ("status", "health")
    search_fields = ("code", "name")


admin.site.register(ProjectMember, SimpleHistoryAdmin)
admin.site.register(Milestone, SimpleHistoryAdmin)
