from django.urls import path

from apps.portal.views import (
    approve_report,
    book_appointment,
    create_medical_record,
    create_report,
    dashboard,
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
    path("appointments/book", book_appointment, name="portal-book-appointment"),
    path(
        "appointments/<uuid:appointment_id>/status",
        update_appointment_status,
        name="portal-update-appointment-status",
    ),
    path("records/create", create_medical_record, name="portal-create-record"),
    path("reports/create", create_report, name="portal-create-report"),
    path("reports/<uuid:report_id>/approve", approve_report, name="portal-approve-report"),
    path("images/upload", upload_image, name="portal-upload-image"),
]
