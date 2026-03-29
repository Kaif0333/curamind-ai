from django.contrib import admin

from apps.appointments.models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "scheduled_time", "status", "created_at")
    list_filter = ("status", "scheduled_time")
    search_fields = (
        "patient__user__email",
        "patient__user__first_name",
        "patient__user__last_name",
        "doctor__user__email",
        "doctor__user__first_name",
        "doctor__user__last_name",
        "reason",
    )
    list_select_related = ("patient__user", "doctor__user")
    autocomplete_fields = ("patient", "doctor")
    date_hierarchy = "scheduled_time"
