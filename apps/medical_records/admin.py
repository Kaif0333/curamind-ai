from django.contrib import admin

from apps.medical_records.models import Diagnosis, MedicalRecord, Prescription


class DiagnosisInline(admin.TabularInline):
    model = Diagnosis
    extra = 0


class PrescriptionInline(admin.TabularInline):
    model = Prescription
    extra = 0


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "created_at")
    search_fields = (
        "patient__user__email",
        "patient__user__first_name",
        "patient__user__last_name",
        "doctor__user__email",
        "doctor__user__first_name",
        "doctor__user__last_name",
        "diagnosis_text",
    )
    list_select_related = ("patient__user", "doctor__user")
    autocomplete_fields = ("patient", "doctor")
    inlines = (DiagnosisInline, PrescriptionInline)
    readonly_fields = ("created_at",)


@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ("medical_record", "created_at")
    search_fields = ("medical_record__patient__user__email", "text")
    autocomplete_fields = ("medical_record",)
    readonly_fields = ("created_at",)


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("medical_record", "medication_name", "dosage", "created_at")
    search_fields = (
        "medical_record__patient__user__email",
        "medication_name",
        "dosage",
        "instructions",
    )
    autocomplete_fields = ("medical_record",)
    readonly_fields = ("created_at",)
