"""
Grade Admin Configuration
"""
from django.contrib import admin
from .models import GradeType, Grade, GradeScale, GradeSummary, GradeAlert, GradeComment


@admin.register(GradeType)
class GradeTypeAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'name', 'max_score', 'weight', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['teacher__username', 'name']


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'grade_type', 'title', 'score', 'max_score',
        'percentage', 'letter_grade', 'grade_date', 'is_published'
    ]
    list_filter = ['grade_type', 'letter_grade', 'is_published', 'grade_date', 'created_at']
    search_fields = ['student__name', 'student__code', 'title']
    readonly_fields = ['percentage', 'letter_grade', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('student', 'grade_type', 'session', 'title', 'description')
        }),
        ('Score', {
            'fields': ('score', 'max_score', 'percentage', 'letter_grade')
        }),
        ('Date & Status', {
            'fields': ('grade_date', 'is_active', 'is_published')
        }),
        ('Feedback', {
            'fields': ('notes', 'feedback')
        }),
        ('System', {
            'fields': ('created_by', 'created_at', 'updated_at')
        })
    )


@admin.register(GradeScale)
class GradeScaleAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'name', 'is_active', 'is_default']
    list_filter = ['is_active', 'is_default']
    search_fields = ['teacher__username', 'name']


@admin.register(GradeSummary)
class GradeSummaryAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'summary_type', 'period_start', 'period_end',
        'total_grades', 'average_percentage', 'overall_letter_grade'
    ]
    list_filter = ['summary_type', 'period_start', 'improvement_trend']
    search_fields = ['student__name', 'student__code']
    readonly_fields = [
        'total_grades', 'average_score', 'average_percentage',
        'overall_letter_grade', 'grade_type_averages', 'class_rank',
        'total_students', 'improvement_trend', 'created_at', 'updated_at'
    ]


@admin.register(GradeAlert)
class GradeAlertAdmin(admin.ModelAdmin):
    list_display = ['student', 'alert_type', 'severity', 'title', 'is_active', 'is_resolved', 'created_at']
    list_filter = ['alert_type', 'severity', 'is_active', 'is_resolved', 'created_at']
    search_fields = ['student__name', 'title', 'message']
    readonly_fields = ['trigger_data', 'resolved_at', 'created_at']


@admin.register(GradeComment)
class GradeCommentAdmin(admin.ModelAdmin):
    list_display = ['grade', 'created_by', 'is_private', 'created_at']
    list_filter = ['is_private', 'created_at']
    search_fields = ['grade__title', 'comment', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']