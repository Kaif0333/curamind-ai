from rest_framework.permissions import BasePermission

from apps.authentication.models import User


class IsRole(BasePermission):
    role: str | None = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == self.role


class IsPatient(IsRole):
    role = User.Role.PATIENT


class IsDoctor(IsRole):
    role = User.Role.DOCTOR


class IsRadiologist(IsRole):
    role = User.Role.RADIOLOGIST


class IsNurse(IsRole):
    role = User.Role.NURSE


class IsAdmin(IsRole):
    role = User.Role.ADMIN
