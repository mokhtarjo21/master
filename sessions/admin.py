"""
Session Admin Configuration
"""
from django.contrib import admin
from .models import Session, SessionReminder, SessionMaterial, SessionNote


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'group', 'date', 'start_time', 'end_time', 
        'status', 'total_students', 'present_count', 'is_active'
    ]
    list_filter = ['status', 'date', 'repeat_type', 'group__group_type', 'is_active']
    search_fields = ['title', 'group__name', 'description']
    readonly_fields = [
        'total_students', 'present_count', 'absent_count', 'late_count',
        'actual_start_time', 'actual_end_time', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('group', 'title', 'description', 'date', 'start_time', 'end_time')
        }),
        ('Status', {
            'fields': ('status', 'actual_start_time', 'actual_end_time')
        }),
        ('Repeat Configuration', {
            'fields': ('repeat_type', 'repeat_until', 'repeat_count', 'parent_session')
        }),
        ('Content', {
            'fields': ('lesson_content', 'homework_assigned', 'materials_used')
        }),
        ('Attendance Summary', {
            'fields': ('total_students', 'present_count', 'absent_count', 'late_count')
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at')
        })
    )


@admin.register(SessionReminder)
class SessionReminderAdmin(admin.ModelAdmin):
    list_display = ['session', 'reminder_type', 'reminder_time', 'is_sent', 'sent_at']
    list_filter = ['reminder_type', 'is_sent', 'created_at']
    search_fields = ['session__title', 'title', 'message']


@admin.register(SessionMaterial)
class SessionMaterialAdmin(admin.ModelAdmin):
    list_display = ['session', 'title', 'file', 'external_link', 'created_at']
    list_filter = ['created_at']
    search_fields = ['session__title', 'title', 'description']


@admin.register(SessionNote)
class SessionNoteAdmin(admin.ModelAdmin):
    list_display = ['session', 'title', 'note_type', 'created_at']
    list_filter = ['note_type', 'created_at']
    search_fields = ['session__title', 'title', 'content']