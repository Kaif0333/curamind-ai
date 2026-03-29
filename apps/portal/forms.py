from __future__ import annotations

import os

from django import forms
from django.contrib.auth import authenticate
from django.db.models import Q
from django.utils import timezone

from apps.authentication.models import User
from apps.authentication.roles import get_self_assignable_role_choices
from apps.appointments.models import Appointment
from apps.doctors.models import DoctorProfile
from apps.medical_records.models import MedicalRecord
from apps.patients.models import PatientProfile
from apps.reports.models import Report


def _display_name_for_user(user: User) -> str:
    full_name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    return full_name or user.email


class DoctorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: DoctorProfile) -> str:
        clinician_name = _display_name_for_user(obj.user)
        specialty = obj.specialty or "General practice"
        return f"{clinician_name} - {specialty}"


class PatientChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: PatientProfile) -> str:
        patient_name = _display_name_for_user(obj.user)
        return f"{patient_name} ({obj.user.email})"


class MedicalRecordChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: MedicalRecord) -> str:
        patient_name = _display_name_for_user(obj.patient.user)
        return f"{patient_name} - {obj.created_at:%b %d, %Y}"


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "you@curamind.ai", "autocomplete": "email"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Enter your password", "autocomplete": "current-password"}
        )
    )

    def authenticate_user(self):
        return authenticate(
            email=self.cleaned_data["email"], password=self.cleaned_data["password"]
        )


class MFALoginForm(forms.Form):
    code = forms.CharField(
        max_length=12,
        help_text="Enter the 6-digit code from your authenticator.",
        widget=forms.TextInput(
            attrs={"placeholder": "123456", "inputmode": "numeric", "autocomplete": "one-time-code"}
        ),
    )


class MFADisableForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Confirm your password", "autocomplete": "current-password"}
        )
    )
    code = forms.CharField(
        max_length=12,
        widget=forms.TextInput(attrs={"placeholder": "123456", "inputmode": "numeric"}),
    )


class RegisterForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "name@example.com", "autocomplete": "email"})
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "First name", "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Last name", "autocomplete": "family-name"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Choose a strong password", "autocomplete": "new-password"}
        )
    )
    role = forms.ChoiceField(
        choices=(), required=False, help_text="Select the account role to request."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = get_self_assignable_role_choices()
        if len(self.fields["role"].choices) <= 1:
            self.fields["role"].widget = forms.HiddenInput()
            self.fields["role"].help_text = ""

    def clean_role(self):
        allow_roles = os.getenv("ALLOW_SELF_ASSIGN_ROLES", "false").lower() == "true"
        if allow_roles:
            return self.cleaned_data.get("role") or User.Role.PATIENT
        return User.Role.PATIENT


class AppointmentCreateForm(forms.ModelForm):
    doctor = DoctorChoiceField(
        queryset=DoctorProfile.objects.none(),
        empty_label="Choose a doctor",
        help_text="Select the clinician you want to see.",
    )
    scheduled_time = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        help_text="Appointments must be scheduled in the future.",
    )

    class Meta:
        model = Appointment
        fields = ("doctor", "scheduled_time", "reason")
        widgets = {
            "reason": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Describe symptoms, concerns, or the reason for this visit.",
                }
            )
        }

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
        widgets = {
            "status": forms.Select(),
        }


class AppointmentCancelForm(forms.Form):
    confirm = forms.BooleanField(required=False)


class MedicalRecordCreateForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        queryset = PatientProfile.objects.none()
        if user and getattr(user, "doctor_profile", None):
            doctor_profile = user.doctor_profile
            queryset = PatientProfile.objects.filter(
                Q(appointments__doctor=doctor_profile) | Q(medical_records__doctor=doctor_profile)
            ).distinct()
        self.fields["patient"] = PatientChoiceField(
            queryset=queryset.select_related("user"),
            empty_label="Choose a patient",
            help_text="Only patients already assigned to you appear here.",
        )

    def clean_patient(self):
        patient = self.cleaned_data["patient"]
        if patient not in self.fields["patient"].queryset:
            raise forms.ValidationError("You can only create records for assigned patients.")
        return patient

    class Meta:
        model = MedicalRecord
        fields = ("patient", "diagnosis_text")
        widgets = {
            "diagnosis_text": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Summarize the visit, findings, and clinical plan.",
                }
            )
        }


class ReportCreateForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = MedicalRecord.objects.none()
        if user and getattr(user, "doctor_profile", None):
            queryset = MedicalRecord.objects.filter(doctor=user.doctor_profile)
        self.fields["medical_record"] = MedicalRecordChoiceField(
            queryset=queryset.select_related("patient__user", "doctor__user"),
            empty_label="Choose a medical record",
            help_text="Only records authored by you are eligible for report drafts.",
        )

    def clean_medical_record(self):
        medical_record = self.cleaned_data["medical_record"]
        if medical_record not in self.fields["medical_record"].queryset:
            raise forms.ValidationError("You can only create reports for your own records.")
        return medical_record

    class Meta:
        model = Report
        fields = ("medical_record", "content")
        widgets = {
            "content": forms.Textarea(
                attrs={"rows": 6, "placeholder": "Draft the report narrative for radiology review."}
            )
        }


class ReportApproveForm(forms.Form):
    approve = forms.BooleanField(required=False)


class DiagnosisCreateForm(forms.Form):
    medical_record = MedicalRecordChoiceField(
        queryset=MedicalRecord.objects.none(),
        empty_label="Choose a medical record",
    )
    text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Add a concise diagnosis note."})
    )

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
    medical_record = MedicalRecordChoiceField(
        queryset=MedicalRecord.objects.none(),
        empty_label="Choose a medical record",
    )
    medication_name = forms.CharField(
        max_length=128,
        widget=forms.TextInput(attrs={"placeholder": "Medication name"}),
    )
    dosage = forms.CharField(
        max_length=64,
        widget=forms.TextInput(attrs={"placeholder": "Dosage, e.g. 5 mg twice daily"}),
    )
    instructions = forms.CharField(
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Administration instructions and follow-up notes."}
        ),
        required=False,
    )

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
    file = forms.FileField(
        help_text="Upload PNG, JPG, or DICOM imaging files.",
        widget=forms.ClearableFileInput(attrs={"accept": ".dcm,.dicom,image/*"}),
    )
    modality = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Optional: MRI, CT, X-Ray, DICOM"}),
    )
