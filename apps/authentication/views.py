from __future__ import annotations

import os

from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.audit_logs.utils import log_action
from apps.authentication.models import LoginAttempt, User
from apps.authentication.serializers import LoginSerializer, RegisterSerializer, UserSerializer

MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_ATTEMPT_TTL = int(os.getenv("LOGIN_ATTEMPT_TTL", "900"))


def _attempt_key(email: str, ip: str | None) -> str:
    return f"login_attempts:{email}:{ip or 'unknown'}"


class RegisterView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_action(user, "register", request, resource_id=str(user.id))
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = []

    def post(self, request, *args, **kwargs):
        email = request.data.get("email", "")
        ip_address = request.META.get("REMOTE_ADDR")
        key = _attempt_key(email, ip_address)
        attempts = cache.get(key, 0)
        if attempts >= MAX_LOGIN_ATTEMPTS:
            return Response(
                {"detail": "Too many login attempts. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            cache.set(key, attempts + 1, timeout=LOGIN_ATTEMPT_TTL)
            LoginAttempt.objects.create(
                user=None,
                email=email,
                ip_address=ip_address,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                success=False,
            )
            raise

        cache.delete(key)
        user: User = serializer.user
        LoginAttempt.objects.create(
            user=user,
            email=user.email,
            ip_address=ip_address,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            success=True,
        )
        log_action(user, "login", request, resource_id=str(user.id))
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RefreshView(TokenRefreshView):
    permission_classes = []


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)
