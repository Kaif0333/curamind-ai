from __future__ import annotations

import os

from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.audit_logs.utils import log_action
from apps.authentication.mfa import (
    build_mfa_provisioning_uri,
    consume_login_challenge,
    create_login_challenge,
    generate_mfa_secret,
    verify_mfa_code,
)
from apps.authentication.models import LoginAttempt, User
from apps.authentication.serializers import (
    LoginSerializer,
    MFACodeSerializer,
    MFADisableSerializer,
    MFALoginVerifySerializer,
    RegisterSerializer,
    UserSerializer,
)

MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_ATTEMPT_TTL = int(os.getenv("LOGIN_ATTEMPT_TTL", "900"))


def _attempt_key(email: str, ip: str | None) -> str:
    return f"login_attempts:{email}:{ip or 'unknown'}"


class RegisterView(APIView):
    permission_classes = ()

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_action(user, "register", request, resource_id=str(user.id))
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = ()

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
        if user.mfa_enabled:
            challenge_token = create_login_challenge(user, ip_address=ip_address)
            log_action(user, "login_mfa_challenge", request, resource_id=str(user.id))
            return Response(
                {
                    "detail": "Multi-factor authentication required.",
                    "mfa_required": True,
                    "challenge_token": challenge_token,
                    "user": serializer.validated_data["user"],
                },
                status=status.HTTP_202_ACCEPTED,
            )

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
    permission_classes = ()


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class MFASetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.mfa_enabled and user.mfa_secret:
            provisioning_uri = build_mfa_provisioning_uri(user, user.mfa_secret)
            return Response(
                {
                    "detail": "MFA is already enabled for this account.",
                    "mfa_enabled": True,
                    "secret": user.mfa_secret,
                    "provisioning_uri": provisioning_uri,
                },
                status=status.HTTP_200_OK,
            )

        user.mfa_secret = generate_mfa_secret()
        user.mfa_enabled = False
        user.save(update_fields=["mfa_secret", "mfa_enabled"])
        provisioning_uri = build_mfa_provisioning_uri(user, user.mfa_secret)
        log_action(user, "mfa_setup_started", request, resource_id=str(user.id))
        return Response(
            {
                "secret": user.mfa_secret,
                "provisioning_uri": provisioning_uri,
                "mfa_enabled": user.mfa_enabled,
            },
            status=status.HTTP_200_OK,
        )


class MFAVerifySetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MFACodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.mfa_secret:
            return Response(
                {"detail": "MFA setup has not been started for this account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not verify_mfa_code(user, serializer.validated_data["code"]):
            return Response(
                {"detail": "Invalid authentication code."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.mfa_enabled = True
        user.save(update_fields=["mfa_enabled"])
        log_action(user, "mfa_enabled", request, resource_id=str(user.id))
        return Response(
            {"detail": "MFA enabled successfully.", "mfa_enabled": True},
            status=status.HTTP_200_OK,
        )


class MFADisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MFADisableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["password"]):
            return Response({"detail": "Invalid password."}, status=status.HTTP_400_BAD_REQUEST)
        if user.mfa_enabled and not verify_mfa_code(user, serializer.validated_data["code"]):
            return Response(
                {"detail": "Invalid authentication code."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.mfa_enabled = False
        user.mfa_secret = ""
        user.save(update_fields=["mfa_enabled", "mfa_secret"])
        log_action(user, "mfa_disabled", request, resource_id=str(user.id))
        return Response(
            {"detail": "MFA disabled successfully.", "mfa_enabled": False},
            status=status.HTTP_200_OK,
        )


class MFALoginVerifyView(APIView):
    permission_classes = ()

    def post(self, request):
        serializer = MFALoginVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        challenge = consume_login_challenge(serializer.validated_data["challenge_token"])
        if not challenge:
            return Response(
                {"detail": "Login challenge expired or is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(id=challenge["user_id"]).first()
        if not user or not user.mfa_enabled:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if not verify_mfa_code(user, serializer.validated_data["code"]):
            return Response(
                {"detail": "Invalid authentication code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = LoginSerializer.get_token(user)
        LoginAttempt.objects.create(
            user=user,
            email=user.email,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            success=True,
        )
        log_action(user, "login", request, resource_id=str(user.id))
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
