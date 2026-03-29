"""URL configuration for CuraMind AI."""

from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.appointments.views import (
    AppointmentCancelView,
    AppointmentCreateView,
    AppointmentStatusUpdateView,
)
from apps.doctors.views import DoctorPatientsView
from apps.imaging.views import ImageUploadView
from apps.medical_records.views import PatientRecordsView
from apps.reports.views import (
    ReportApproveView,
    ReportCreateView,
    ReportDownloadView,
    ReportListView,
)

admin.site.site_header = "CuraMind AI Control Center"
admin.site.site_title = "CuraMind AI Admin"
admin.site.index_title = "Clinical operations and platform management"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("auth/", include("apps.authentication.urls")),
    path("patients/", include("apps.patients.urls")),
    path("doctors/", include("apps.doctors.urls")),
    path("records/", include("apps.medical_records.urls")),
    path("imaging/", include("apps.imaging.urls")),
    re_path(r"^appointments/?$", AppointmentCreateView.as_view(), name="appointments-create"),
    re_path(
        r"^appointments/(?P<appointment_id>[0-9a-f-]+)/cancel/?$",
        AppointmentCancelView.as_view(),
        name="appointment-cancel",
    ),
    re_path(
        r"^appointments/(?P<appointment_id>[0-9a-f-]+)/status/?$",
        AppointmentStatusUpdateView.as_view(),
        name="appointment-status",
    ),
    re_path(r"^reports/?$", ReportListView.as_view(), name="reports-list"),
    re_path(r"^reports/create/?$", ReportCreateView.as_view(), name="report-create"),
    re_path(
        r"^reports/(?P<report_id>[0-9a-f-]+)/download/?$",
        ReportDownloadView.as_view(),
        name="report-download",
    ),
    re_path(
        r"^reports/(?P<report_id>[0-9a-f-]+)/approve/?$",
        ReportApproveView.as_view(),
        name="report-approve",
    ),
    path("audit-logs", include("apps.audit_logs.urls")),
    path("ai/", include("apps.ai_engine.urls")),
    path("upload-image", ImageUploadView.as_view(), name="upload-image"),
    path("patient/records", PatientRecordsView.as_view(), name="patient-records"),
    path("doctor/patients", DoctorPatientsView.as_view(), name="doctor-patients"),
    path("", include("apps.portal.urls")),
]
