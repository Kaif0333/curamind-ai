from django.contrib import admin

from apps.imaging.models import MedicalImage


@admin.register(MedicalImage)
class MedicalImageAdmin(admin.ModelAdmin):
    list_display = ("file_name", "patient", "modality", "status", "uploaded_at")
    list_filter = ("status", "modality", "uploaded_at")
    search_fields = (
        "file_name",
        "patient__user__email",
        "patient__user__first_name",
        "patient__user__last_name",
        "s3_key",
    )
    list_select_related = ("patient__user", "uploaded_by")
    autocomplete_fields = ("patient", "uploaded_by")
    readonly_fields = ("uploaded_at", "metadata")
