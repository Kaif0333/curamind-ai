from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit_logs.models import AuditLog
from apps.audit_logs.serializers import AuditLogListQuerySerializer, AuditLogSerializer
from apps.authentication.permissions import IsAdmin


class AuditLogListView(APIView):
    permission_classes = [IsAdmin]
    serializer_class = AuditLogSerializer

    @extend_schema(
        parameters=[AuditLogListQuerySerializer],
        responses=AuditLogSerializer(many=True),
    )
    def get(self, request):
        query_serializer = AuditLogListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        filters = query_serializer.validated_data

        logs = AuditLog.objects.select_related("user").all()

        if filters.get("action"):
            logs = logs.filter(action__iexact=filters["action"])
        if filters.get("email"):
            logs = logs.filter(user__email__icontains=filters["email"])
        if filters.get("resource_id"):
            logs = logs.filter(resource_id=filters["resource_id"])

        logs = logs.order_by("-timestamp")[: filters["limit"]]
        return Response(AuditLogSerializer(logs, many=True).data, status=status.HTTP_200_OK)
