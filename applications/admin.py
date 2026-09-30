from django.contrib import admin
from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("company", "role", "status", "date_applied")
    list_filter = ("status",)
    search_fields = ("company", "role")