from django.contrib import admin
from .models import Application, ApplicationStatusHistory


class StatusHistoryInline(admin.TabularInline):
    model = ApplicationStatusHistory
    fields = ("previous_status", "status", "recorded_at", "is_baseline")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("company", "role", "status", "date_applied")
    list_filter = ("status",)
    search_fields = ("company", "role")
    inlines = [StatusHistoryInline]
