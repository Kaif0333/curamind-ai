from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.schemas import get_schema_view
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONOpenAPIRenderer

from users.forms import LoginForm
from users.views import register_patient, register_doctor
from .views import home, docs, routes, health

schema_view = get_schema_view(
    title="CuraMind AI API",
    description="Appointment and authentication API",
    version="1.0.0",
    public=True,
    permission_classes=[AllowAny],
    renderer_classes=[JSONOpenAPIRenderer],
)


staff_or_superuser_required = user_passes_test(
    lambda u: u.is_authenticated and (u.is_staff or u.is_superuser),
    login_url='/accounts/login/',
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('health/', health, name='health'),
    path('docs/', staff_or_superuser_required(docs), name='docs'),
    path('routes/', staff_or_superuser_required(routes), name='routes'),

    path('users/', include('users.urls')),
    path('api/schema/', staff_or_superuser_required(schema_view), name='api_schema'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('doctor/', RedirectView.as_view(pattern_name='doctor_dashboard', permanent=False)),
    path('patient/', RedirectView.as_view(pattern_name='patient_dashboard', permanent=False)),
    path('appointments/', RedirectView.as_view(pattern_name='role_redirect', permanent=False)),
    path('book/', RedirectView.as_view(pattern_name='book_appointment', permanent=False)),
    path('accounts/', RedirectView.as_view(pattern_name='login', permanent=False)),
    path('login/', RedirectView.as_view(pattern_name='login', permanent=False)),
    path('logout/', RedirectView.as_view(pattern_name='logout', permanent=False)),
    path('register/', RedirectView.as_view(pattern_name='register', permanent=False)),
    path('register/doctor/', RedirectView.as_view(pattern_name='register_doctor', permanent=False)),
    path('accounts/register/', register_patient, name='register'),
    path('accounts/register/doctor/', register_doctor, name='register_doctor'),

    path(
        'accounts/login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html',
            authentication_form=LoginForm,
        ),
        name='login'
    ),
    path(
        'accounts/logout/',
        auth_views.LogoutView.as_view(),
        name='logout'
    ),
]
