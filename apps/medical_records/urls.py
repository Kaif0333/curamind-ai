from django.urls import path

from apps.medical_records.views import MedicalRecordCreateView, PatientRecordsView

urlpatterns = [
    path("patient", PatientRecordsView.as_view(), name="patient-records"),
    path("create", MedicalRecordCreateView.as_view(), name="record-create"),
]
