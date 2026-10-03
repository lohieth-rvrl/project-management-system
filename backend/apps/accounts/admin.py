from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import User


@admin.register(User)
class PMSUserAdmin(UserAdmin, SimpleHistoryAdmin):
    fieldsets = UserAdmin.fieldsets + (("PMS", {"fields": ("role", "weekly_capacity_hours")}),)
    list_display = ("username", "email", "role", "is_active")
    list_filter = ("role", "is_active")
