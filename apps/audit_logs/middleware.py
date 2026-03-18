from apps.audit_logs.utils import log_action


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            log_action(request.user, f"http_{request.method.lower()}", request)
        return response
