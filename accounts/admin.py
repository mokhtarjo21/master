"""
User Admin Configuration
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, TeacherSession, StudentAccessLog

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Extended User Admin"""
    
    list_display = [
        'username', 'email', 'user_type', 
        'center_name', 'student_code', 
        'is_active', 'last_activity'
    ]

    list_filter = ['user_type', 'is_active', 'language', 'created_at']
    search_fields = ['username', 'email', 'center_name', 'student_code']
    ordering = ['-created_at']

    readonly_fields = ('last_activity',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {
            'fields': ('user_type', 'language', 'center_name', 'student_code')
        }),
        ('Authentication', {
            'fields': ('teacher_pin', 'access_token', 'qr_token', 'qr_expires_at')
        }),
        ('Activity', {
            'fields': ('last_activity', 'is_active_session')
        }),
    )

@admin.register(TeacherSession)
class TeacherSessionAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'session_token', 'created_at', 'expires_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['teacher__username', 'session_token']
    readonly_fields = ['session_token', 'created_at']


@admin.register(StudentAccessLog)
class StudentAccessLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'access_method', 'success', 'ip_address', 'created_at']
    list_filter = ['access_method', 'success', 'created_at']
    search_fields = ['user__username', 'ip_address']
    readonly_fields = ['created_at']