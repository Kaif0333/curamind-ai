from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit_logs.models import AuditLog
from apps.audit_logs.serializers import AuditLogSerializer
from apps.authentication.permissions import IsAdmin


class AuditLogListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        logs = AuditLog.objects.select_related("user").all()

        action = request.query_params.get("action")
        email = request.query_params.get("email")
        resource_id = request.query_params.get("resource_id")
        limit = min(int(request.query_params.get("limit", 100)), 200)

        if action:
            logs = logs.filter(action__iexact=action)
        if email:
            logs = logs.filter(user__email__icontains=email)
        if resource_id:
            logs = logs.filter(resource_id=resource_id)

        logs = logs.order_by("-timestamp")[:limit]
        return Response(AuditLogSerializer(logs, many=True).data, status=status.HTTP_200_OK)
