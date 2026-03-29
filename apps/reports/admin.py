from django.contrib import admin

from apps.reports.models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "medical_record", "author", "status", "created_at", "approved_at")
    list_filter = ("status", "created_at", "approved_at")
    search_fields = (
        "medical_record__patient__user__email",
        "medical_record__doctor__user__email",
        "author__email",
        "content",
    )
    list_select_related = (
        "medical_record__patient__user",
        "medical_record__doctor__user",
        "author",
    )
    autocomplete_fields = ("medical_record", "author")
    readonly_fields = ("created_at", "approved_at")
