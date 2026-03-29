from django.contrib import admin

from apps.patients.models import PatientProfile


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "emergency_contact", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "phone")
    list_select_related = ("user",)
