from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

from .views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),

    path('users/', include('users.urls')),

    path(
        'accounts/login/',
        auth_views.LoginView.as_view(template_name='registration/login.html'),
        name='login'
    ),
    path(
        'accounts/logout/',
        auth_views.LogoutView.as_view(),
        name='logout'
    ),
]
