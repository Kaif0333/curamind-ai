from django.urls import path

from apps.portal.views import (
    add_diagnosis,
    add_prescription,
    approve_report,
    book_appointment,
    cancel_appointment,
    create_medical_record,
    create_report,
    dashboard,
    download_image,
    download_report,
    home,
    login_view,
    logout_view,
    register_view,
    update_appointment_status,
    upload_image,
)

urlpatterns = [
    path("", home, name="portal-home"),
    path("login", login_view, name="portal-login"),
    path("logout", logout_view, name="portal-logout"),
    path("register", register_view, name="portal-register"),
    path("dashboard", dashboard, name="portal-dashboard"),
    path("dashboard/images/<uuid:image_id>/download", download_image, name="portal-download-image"),
    path("dashboard/appointments/book", book_appointment, name="portal-book-appointment"),
    path(
        "dashboard/appointments/<uuid:appointment_id>/cancel",
        cancel_appointment,
        name="portal-cancel-appointment",
    ),
    path(
        "dashboard/appointments/<uuid:appointment_id>/status",
        update_appointment_status,
        name="portal-update-appointment-status",
    ),
    path("dashboard/records/create", create_medical_record, name="portal-create-record"),
    path("dashboard/records/diagnoses/create", add_diagnosis, name="portal-add-diagnosis"),
    path(
        "dashboard/records/prescriptions/create",
        add_prescription,
        name="portal-add-prescription",
    ),
    path("dashboard/reports/create", create_report, name="portal-create-report"),
    path(
        "dashboard/reports/<uuid:report_id>/download",
        download_report,
        name="portal-download-report",
    ),
    path(
        "dashboard/reports/<uuid:report_id>/approve",
        approve_report,
        name="portal-approve-report",
    ),
    path("dashboard/images/upload", upload_image, name="portal-upload-image"),
]
