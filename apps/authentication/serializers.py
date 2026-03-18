from __future__ import annotations

import os

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.authentication.models import User


def _self_assignable_roles() -> set[str]:
    allow_roles = os.getenv("ALLOW_SELF_ASSIGN_ROLES", "false").lower() == "true"
    if not allow_roles:
        return {User.Role.PATIENT}

    configured_roles = {
        role.strip()
        for role in os.getenv(
            "SELF_ASSIGNABLE_ROLES",
            ",".join(
                [
                    User.Role.PATIENT,
                    User.Role.DOCTOR,
                    User.Role.RADIOLOGIST,
                    User.Role.NURSE,
                ]
            ),
        ).split(",")
        if role.strip()
    }
    configured_roles.discard(User.Role.ADMIN)
    return configured_roles or {User.Role.PATIENT}


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name", "role")

    def validate_role(self, value: str) -> str:
        if value in _self_assignable_roles():
            return value
        return User.Role.PATIENT

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
    def get_token(cls, user: User):
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
        data = super().validate(attrs)
        data["user"] = UserSerializer(user).data
        return data
