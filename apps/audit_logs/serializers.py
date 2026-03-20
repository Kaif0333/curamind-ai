from rest_framework import serializers

from apps.audit_logs.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "user",
            "user_email",
            "action",
            "timestamp",
            "ip_address",
            "resource_id",
            "metadata",
        )
        read_only_fields = fields


class AuditLogListQuerySerializer(serializers.Serializer):
    action = serializers.CharField(required=False, allow_blank=False)
    email = serializers.CharField(required=False, allow_blank=False)
    resource_id = serializers.CharField(required=False, allow_blank=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=200, default=100)
