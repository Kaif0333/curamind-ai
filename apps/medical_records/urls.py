from django.urls import path

from apps.medical_records.views import (
    MedicalRecordCreateView,
    PatientRecordsView,
    RecordDiagnosesView,
    RecordPrescriptionsView,
)

urlpatterns = [
    path("patient", PatientRecordsView.as_view(), name="patient-records"),
    path("create", MedicalRecordCreateView.as_view(), name="record-create"),
    path("<uuid:record_id>/diagnoses", RecordDiagnosesView.as_view(), name="record-diagnoses"),
    path(
        "<uuid:record_id>/prescriptions",
        RecordPrescriptionsView.as_view(),
        name="record-prescriptions",
    ),
]
