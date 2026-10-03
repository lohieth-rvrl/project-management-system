from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Comment, Sprint, Task, TaskDependency


@admin.register(Task)
class TaskAdmin(SimpleHistoryAdmin):
    list_display = ("title", "project", "status", "priority", "assignee", "due_date")
    list_filter = ("status", "priority", "project")
    search_fields = ("title",)


admin.site.register(Sprint, SimpleHistoryAdmin)
admin.site.register(TaskDependency)
admin.site.register(Comment)
