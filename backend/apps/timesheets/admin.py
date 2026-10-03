from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import TimeEntry

admin.site.register(TimeEntry, SimpleHistoryAdmin)
