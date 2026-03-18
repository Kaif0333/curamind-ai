"""URL configuration for CuraMind AI."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.appointments.views import AppointmentCreateView
from apps.doctors.views import DoctorPatientsView
from apps.imaging.views import ImageUploadView
from apps.medical_records.views import PatientRecordsView
from apps.reports.views import ReportListView
from apps.ai_engine.views import AIResultView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("auth/", include("apps.authentication.urls")),
    path("patients/", include("apps.patients.urls")),
    path("doctors/", include("apps.doctors.urls")),
    path("appointments/", include("apps.appointments.urls")),
    path("records/", include("apps.medical_records.urls")),
    path("imaging/", include("apps.imaging.urls")),
    path("reports/", include("apps.reports.urls")),
    path("ai/", include("apps.ai_engine.urls")),
    path("upload-image", ImageUploadView.as_view(), name="upload-image"),
    path("patient/records", PatientRecordsView.as_view(), name="patient-records"),
    path("doctor/patients", DoctorPatientsView.as_view(), name="doctor-patients"),
    path("appointments", AppointmentCreateView.as_view(), name="appointments-create"),
    path("reports", ReportListView.as_view(), name="reports-list"),
    path("ai-result", AIResultView.as_view(), name="ai-result"),
    path("", include("apps.portal.urls")),
]
