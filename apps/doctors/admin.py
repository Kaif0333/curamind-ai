from django.contrib import admin

from apps.doctors.models import DoctorProfile


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specialty", "department", "license_number", "created_at")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "specialty",
        "department",
        "license_number",
    )
    list_filter = ("specialty", "department")
    list_select_related = ("user",)
