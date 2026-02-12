"""
Attendance Admin Configuration
"""
from django.contrib import admin
from .models import Attendance, AttendanceQRCode, AttendanceSummary, AttendanceAlert


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'session', 'status', 'method', 'marked_at', 'arrival_time'
    ]
    list_filter = ['status', 'method', 'marked_at']
    search_fields = ['student__name', 'student__code', 'session__title']
    readonly_fields = ['marked_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('session', 'student', 'status', 'method')
        }),
        ('Timing', {
            'fields': ('marked_at', 'arrival_time')
        }),
        ('Additional Information', {
            'fields': ('notes', 'excuse_reason', 'qr_token')
        }),
        ('System', {
            'fields': ('marked_by', 'created_at', 'updated_at')
        })
    )


@admin.register(AttendanceQRCode)
class AttendanceQRCodeAdmin(admin.ModelAdmin):
    list_display = ['session', 'qr_token', 'valid_from', 'valid_until', 'is_active', 'scan_count']
    list_filter = ['is_active', 'valid_from', 'created_at']
    search_fields = ['session__title', 'qr_token']
    readonly_fields = ['qr_token', 'scan_count', 'created_at']


@admin.register(AttendanceSummary)
class AttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'summary_type', 'period_start', 'period_end',
        'attendance_rate', 'punctuality_rate'
    ]
    list_filter = ['summary_type', 'period_start']
    search_fields = ['student__name', 'student__code']
    readonly_fields = ['attendance_rate', 'punctuality_rate', 'created_at', 'updated_at']


@admin.register(AttendanceAlert)
class AttendanceAlertAdmin(admin.ModelAdmin):
    list_display = ['student', 'alert_type', 'severity', 'is_active', 'is_resolved', 'created_at']
    list_filter = ['alert_type', 'severity', 'is_active', 'is_resolved', 'created_at']
    search_fields = ['student__name', 'title', 'message']
    readonly_fields = ['trigger_data', 'resolved_at', 'created_at']