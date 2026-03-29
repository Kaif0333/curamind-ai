from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from guardian.shortcuts import assign_perm
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit_logs.utils import log_action
from apps.authentication.models import User
from apps.authentication.permissions import IsDoctor, IsRadiologist
from apps.medical_records.models import MedicalRecord
from apps.notifications.tasks import send_email_notification
from apps.reports.models import Report
from apps.reports.serializers import (
    ReportApproveSerializer,
    ReportCreateSerializer,
    ReportSerializer,
)


def _get_reports_for_user(user):
    if user.role == User.Role.PATIENT:
        return Report.objects.filter(
            medical_record__patient__user=user,
            status=Report.Status.APPROVED,
        )
    if user.role == User.Role.DOCTOR:
        return Report.objects.filter(author=user)
    if user.role in {User.Role.RADIOLOGIST, User.Role.ADMIN}:
        return Report.objects.all()
    return Report.objects.none()


def _get_report_for_user(user, report_id: str) -> Report | None:
    return (
        _get_reports_for_user(user)
        .select_related(
            "author",
            "medical_record__patient__user",
            "medical_record__doctor__user",
        )
        .filter(id=report_id)
        .first()
    )


class ReportListView(APIView):
    serializer_class = ReportSerializer

    @extend_schema(responses=ReportSerializer(many=True))
    def get(self, request):
        user = request.user
        reports = _get_reports_for_user(user).select_related(
            "author",
            "medical_record__patient__user",
            "medical_record__doctor__user",
        )
        log_action(user, "report_view", request)
        return Response(ReportSerializer(reports, many=True).data, status=status.HTTP_200_OK)


class ReportCreateView(APIView):
    permission_classes = [IsDoctor]
    serializer_class = ReportCreateSerializer

    @extend_schema(request=ReportCreateSerializer, responses=ReportSerializer)
    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = MedicalRecord.objects.filter(
            id=serializer.validated_data["medical_record_id"]
        ).first()
        if not record:
            return Response(
                {"detail": "Medical record not found"}, status=status.HTTP_404_NOT_FOUND
            )
        if record.doctor.user != request.user:
            return Response(
                {"detail": "You can only create reports for your own medical records."},
                status=status.HTTP_403_FORBIDDEN,
            )

        report = Report.objects.create(
            medical_record=record,
            author=request.user,
            content=serializer.validated_data["content"],
            status=Report.Status.DRAFT,
        )
        assign_perm("view_report", request.user, report)
        assign_perm("change_report", request.user, report)
        assign_perm("view_report", record.patient.user, report)
        log_action(request.user, "report_create", request, resource_id=str(report.id))
        send_email_notification.delay(
            record.patient.user.email,
            "New report draft available",
            "A new medical report draft has been created for your record.",
        )
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


class ReportApproveView(APIView):
    permission_classes = [IsRadiologist]
    serializer_class = ReportApproveSerializer

    @extend_schema(request=ReportApproveSerializer, responses=ReportSerializer)
    def patch(self, request, report_id: str):
        report = Report.objects.filter(id=report_id).first()
        if not report:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        if report.status != Report.Status.DRAFT:
            return Response(
                {"detail": "Only draft reports can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ReportApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("approve"):
            report.status = Report.Status.APPROVED
            report.approved_at = timezone.now()
            report.save(update_fields=["status", "approved_at"])
            log_action(request.user, "report_approve", request, resource_id=str(report.id))
            send_email_notification.delay(
                report.medical_record.patient.user.email,
                "Report approved",
                "Your medical report has been approved by a radiologist.",
            )
        return Response(ReportSerializer(report).data, status=status.HTTP_200_OK)


class ReportDownloadView(APIView):
    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.STR,
                description="Plain-text report export.",
            )
        }
    )
    def get(self, request, report_id: str):
        if request.user.role == User.Role.ADMIN:
            return Response(
                {"detail": "Administrators cannot download private patient reports."},
                status=status.HTTP_403_FORBIDDEN,
            )

        report = _get_report_for_user(request.user, report_id)
        if not report:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)

        patient = report.medical_record.patient.user
        doctor = report.medical_record.doctor.user
        author = report.author.email if report.author else "Unknown"
        body = "\n".join(
            [
                f"CuraMind AI Report ID: {report.id}",
                f"Status: {report.status}",
                f"Author: {author}",
                f"Patient: {patient.email}",
                f"Doctor: {doctor.email}",
                f"Created At: {report.created_at.isoformat()}",
                (
                    "Approved At: "
                    f"{report.approved_at.isoformat() if report.approved_at else 'Pending'}"
                ),
                "",
                "Report Content",
                "==============",
                report.content,
                "",
            ]
        )
        response = HttpResponse(body, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="curamind-report-{report.id}.txt"'
        log_action(request.user, "report_download", request, resource_id=str(report.id))
        return response
