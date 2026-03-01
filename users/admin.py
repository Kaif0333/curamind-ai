from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, Appointment

admin.site.site_header = "CuraMind Control Center"
admin.site.site_title = "CuraMind Admin"
admin.site.index_title = "Operations"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ('username', 'email', 'user_type', 'is_staff', 'is_superuser')
    list_filter = ('user_type',)
    search_fields = ('username', 'email')
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Role', {'fields': ('user_type',)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ('Role', {'fields': ('user_type',)}),
    )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'date', 'time', 'status')
    list_filter = ('status', 'doctor')
    search_fields = ('patient__username', 'doctor__username')
