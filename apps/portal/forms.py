from __future__ import annotations

import os

from django import forms
from django.contrib.auth import authenticate

from apps.authentication.models import User
from apps.appointments.models import Appointment
from apps.doctors.models import DoctorProfile
from apps.medical_records.models import MedicalRecord
from apps.reports.models import Report


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def authenticate_user(self):
        return authenticate(
            email=self.cleaned_data["email"], password=self.cleaned_data["password"]
        )


class RegisterForm(forms.Form):
    email = forms.EmailField()
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=[(User.Role.PATIENT, "Patient")], required=False)

    def clean_role(self):
        allow_roles = os.getenv("ALLOW_SELF_ASSIGN_ROLES", "false").lower() == "true"
        if allow_roles:
            return self.cleaned_data.get("role") or User.Role.PATIENT
        return User.Role.PATIENT


class AppointmentCreateForm(forms.ModelForm):
    doctor = forms.ModelChoiceField(queryset=DoctorProfile.objects.all())
    scheduled_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )

    class Meta:
        model = Appointment
        fields = ("doctor", "scheduled_time", "reason")


class AppointmentStatusForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ("status",)


class MedicalRecordCreateForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ("patient", "diagnosis_text")


class ReportCreateForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ("medical_record", "content")


class ReportApproveForm(forms.Form):
    approve = forms.BooleanField(required=False)


class ImageUploadForm(forms.Form):
    file = forms.FileField()
    modality = forms.CharField(required=False)
