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
