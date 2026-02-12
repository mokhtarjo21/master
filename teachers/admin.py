"""
Teacher Admin Configuration
"""
from django.contrib import admin
from .models import TeacherProfile, TeacherStats, TeacherNotificationSettings


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ['center_name', 'user', 'subscription_plan', 'max_students', 'max_groups', 'created_at']
    list_filter = ['subscription_plan', 'default_language', 'smart_insights_enabled', 'created_at']
    search_fields = ['center_name', 'user__username', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TeacherStats)
class TeacherStatsAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'date', 'stat_type', 'total_students', 'total_revenue', 'attendance_rate']
    list_filter = ['stat_type', 'date', 'created_at']
    search_fields = ['teacher__username']
    readonly_fields = ['created_at']
    
    def attendance_rate(self, obj):
        if obj.total_attendance > 0:
            return f"{(obj.present_count / obj.total_attendance) * 100:.1f}%"
        return "0%"


@admin.register(TeacherNotificationSettings)
class TeacherNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'payment_received_email', 'session_reminder_whatsapp', 'smart_alerts_email']
    list_filter = ['payment_received_email', 'session_reminder_whatsapp', 'smart_alerts_email']
    search_fields = ['teacher__username']