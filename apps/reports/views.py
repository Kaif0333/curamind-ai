from django.utils import timezone
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


class ReportListView(APIView):
    def get(self, request):
        user = request.user
        if user.role == User.Role.PATIENT:
            reports = Report.objects.filter(medical_record__patient__user=user)
        elif user.role in {User.Role.DOCTOR, User.Role.RADIOLOGIST}:
            reports = Report.objects.filter(author=user)
        else:
            reports = Report.objects.all()
        log_action(user, "report_view", request)
        return Response(ReportSerializer(reports, many=True).data, status=status.HTTP_200_OK)


class ReportCreateView(APIView):
    permission_classes = [IsDoctor]

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

    def patch(self, request, report_id: str):
        report = Report.objects.filter(id=report_id).first()
        if not report:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
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
