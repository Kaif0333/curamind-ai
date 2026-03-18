from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from apps.audit_logs.models import AuditLog


def log_action(
    user,
    action: str,
    request: HttpRequest | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    ip_address = None
    if request:
        ip_address = request.META.get("REMOTE_ADDR")
    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        ip_address=ip_address,
        resource_id=resource_id or "",
        metadata=metadata or {},
    )
