from __future__ import annotations

import os

from django import forms
from django.contrib.auth import authenticate
from django.utils import timezone

from apps.authentication.models import User
from apps.appointments.models import Appointment
from apps.doctors.models import DoctorProfile
from apps.medical_records.models import MedicalRecord
from apps.patients.models import PatientProfile
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
    doctor = forms.ModelChoiceField(queryset=DoctorProfile.objects.none())
    scheduled_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )

    class Meta:
        model = Appointment
        fields = ("doctor", "scheduled_time", "reason")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = DoctorProfile.objects.filter(
            user__role=User.Role.DOCTOR
        ).select_related("user")

    def clean_scheduled_time(self):
        scheduled_time = self.cleaned_data["scheduled_time"]
        if scheduled_time <= timezone.now():
            raise forms.ValidationError("Appointments must be scheduled in the future.")
        return scheduled_time


class AppointmentStatusForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ("status",)


class AppointmentCancelForm(forms.Form):
    confirm = forms.BooleanField(required=False)


class MedicalRecordCreateForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        queryset = PatientProfile.objects.none()
        if user and getattr(user, "doctor_profile", None):
            doctor_profile = user.doctor_profile
            queryset = PatientProfile.objects.filter(appointments__doctor=doctor_profile).distinct()
        self.fields["patient"].queryset = queryset.select_related("user")

    def clean_patient(self):
        patient = self.cleaned_data["patient"]
        if patient not in self.fields["patient"].queryset:
            raise forms.ValidationError("You can only create records for assigned patients.")
        return patient

    class Meta:
        model = MedicalRecord
        fields = ("patient", "diagnosis_text")


class ReportCreateForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = MedicalRecord.objects.none()
        if user and getattr(user, "doctor_profile", None):
            queryset = MedicalRecord.objects.filter(doctor=user.doctor_profile)
        self.fields["medical_record"].queryset = queryset.select_related("patient", "doctor")

    def clean_medical_record(self):
        medical_record = self.cleaned_data["medical_record"]
        if medical_record not in self.fields["medical_record"].queryset:
            raise forms.ValidationError("You can only create reports for your own records.")
        return medical_record

    class Meta:
        model = Report
        fields = ("medical_record", "content")


class ReportApproveForm(forms.Form):
    approve = forms.BooleanField(required=False)


class DiagnosisCreateForm(forms.Form):
    medical_record = forms.ModelChoiceField(queryset=MedicalRecord.objects.none())
    text = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = MedicalRecord.objects.none()
        if user and getattr(user, "doctor_profile", None):
            queryset = MedicalRecord.objects.filter(doctor=user.doctor_profile)
        self.fields["medical_record"].queryset = queryset.select_related("patient", "doctor")

    def clean_medical_record(self):
        medical_record = self.cleaned_data["medical_record"]
        if medical_record not in self.fields["medical_record"].queryset:
            raise forms.ValidationError("You can only update your own records.")
        return medical_record


class PrescriptionCreateForm(forms.Form):
    medical_record = forms.ModelChoiceField(queryset=MedicalRecord.objects.none())
    medication_name = forms.CharField(max_length=128)
    dosage = forms.CharField(max_length=64)
    instructions = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = MedicalRecord.objects.none()
        if user and getattr(user, "doctor_profile", None):
            queryset = MedicalRecord.objects.filter(doctor=user.doctor_profile)
        self.fields["medical_record"].queryset = queryset.select_related("patient", "doctor")

    def clean_medical_record(self):
        medical_record = self.cleaned_data["medical_record"]
        if medical_record not in self.fields["medical_record"].queryset:
            raise forms.ValidationError("You can only update your own records.")
        return medical_record


class ImageUploadForm(forms.Form):
    file = forms.FileField()
    modality = forms.CharField(required=False)
