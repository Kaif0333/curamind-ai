from __future__ import annotations

from typing import cast

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.authentication.mfa import normalize_mfa_code
from apps.authentication.models import User
from apps.authentication.roles import get_self_assignable_roles


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "mfa_enabled")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name", "role")

    def validate_role(self, value: str) -> str:
        if value in get_self_assignable_roles():
            return value
        return cast(str, User.Role.PATIENT)

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        role = user.role
        if role == User.Role.PATIENT:
            from apps.patients.models import PatientProfile

            PatientProfile.objects.create(user=user)
        elif role == User.Role.DOCTOR or role == User.Role.RADIOLOGIST:
            from apps.doctors.models import DoctorProfile

            DoctorProfile.objects.create(user=user, specialty="")
        return user


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["email"] = user.email
        return token

    def validate(self, attrs):
        credentials = {
            "email": attrs.get("email"),
            "password": attrs.get("password"),
        }
        user = authenticate(**credentials)
        if user is None:
            raise serializers.ValidationError("Invalid credentials")
        self.user = user
        data = {"user": UserSerializer(user).data}
        if not user.mfa_enabled:
            refresh = self.get_token(user)
            data["refresh"] = str(refresh)
            data["access"] = str(refresh.access_token)
            return data
        data["mfa_required"] = True
        return data


class MFACodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=12)

    def validate_code(self, value: str) -> str:
        normalized = normalize_mfa_code(value)
        if len(normalized) != 6:
            raise serializers.ValidationError("Enter a valid 6-digit authentication code.")
        return normalized


class MFADisableSerializer(MFACodeSerializer):
    password = serializers.CharField(write_only=True)


class MFALoginVerifySerializer(MFACodeSerializer):
    challenge_token = serializers.CharField()


class MFASetupResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(required=False)
    secret = serializers.CharField()
    provisioning_uri = serializers.CharField()
    mfa_enabled = serializers.BooleanField()


class MFAStatusSerializer(serializers.Serializer):
    detail = serializers.CharField()
    mfa_enabled = serializers.BooleanField()


class MFALoginChallengeSerializer(serializers.Serializer):
    detail = serializers.CharField()
    mfa_required = serializers.BooleanField()
    challenge_token = serializers.CharField()
    user = UserSerializer()


class AuthTokenResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()
    user = UserSerializer()
