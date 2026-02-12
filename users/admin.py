from django.contrib import admin
from .models import User, Appointment


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'user_type', 'is_staff')
    list_filter = ('user_type',)
    search_fields = ('username',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'date', 'time', 'status')
    list_filter = ('status', 'doctor')
    search_fields = ('patient__username', 'doctor__username')
