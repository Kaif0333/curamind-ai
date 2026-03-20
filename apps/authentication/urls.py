from django.urls import path

from apps.authentication.views import (
    LoginView,
    MeView,
    MFADisableView,
    MFALoginVerifyView,
    MFASetupView,
    MFAVerifySetupView,
    RefreshView,
    RegisterView,
)

urlpatterns = [
    path("register", RegisterView.as_view(), name="auth-register"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("login/mfa-verify", MFALoginVerifyView.as_view(), name="auth-login-mfa-verify"),
    path("mfa/setup", MFASetupView.as_view(), name="auth-mfa-setup"),
    path("mfa/verify", MFAVerifySetupView.as_view(), name="auth-mfa-verify"),
    path("mfa/disable", MFADisableView.as_view(), name="auth-mfa-disable"),
    path("refresh", RefreshView.as_view(), name="auth-refresh"),
    path("me", MeView.as_view(), name="auth-me"),
]
