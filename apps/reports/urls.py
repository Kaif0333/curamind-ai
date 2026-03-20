from django.urls import path

from apps.reports.views import (
    ReportApproveView,
    ReportCreateView,
    ReportDownloadView,
    ReportListView,
)

urlpatterns = [
    path("", ReportListView.as_view(), name="report-list"),
    path("create", ReportCreateView.as_view(), name="report-create"),
    path("<uuid:report_id>/download", ReportDownloadView.as_view(), name="report-download"),
    path("<uuid:report_id>/approve", ReportApproveView.as_view(), name="report-approve"),
]
