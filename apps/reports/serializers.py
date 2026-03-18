from rest_framework import serializers

from apps.reports.models import Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = (
            "id",
            "medical_record",
            "author",
            "status",
            "content",
            "created_at",
            "approved_at",
        )
        read_only_fields = ("id", "created_at", "approved_at")


class ReportCreateSerializer(serializers.Serializer):
    medical_record_id = serializers.UUIDField()
    content = serializers.CharField()


class ReportApproveSerializer(serializers.Serializer):
    approve = serializers.BooleanField(default=True)
