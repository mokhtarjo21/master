"""
Points Admin
"""
from django.contrib import admin
from .models import PointRule, Prize, StudentPoints, PointTransaction


@admin.register(PointRule)
class PointRuleAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'event_type', 'points', 'group', 'is_active']
    list_filter = ['event_type', 'is_active', 'teacher']
    search_fields = ['teacher__username', 'description']


@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ['name', 'teacher', 'points_required', 'is_active']
    list_filter = ['is_active', 'teacher']
    search_fields = ['name', 'teacher__username']
    ordering = ['points_required']


@admin.register(StudentPoints)
class StudentPointsAdmin(admin.ModelAdmin):
    list_display = ['student', 'teacher', 'total_points', 'total_earned', 'total_deducted', 'last_updated']
    list_filter = ['teacher']
    search_fields = ['student__name', 'student__code']
    ordering = ['-total_points']
    readonly_fields = ['total_points', 'total_earned', 'total_deducted', 'last_updated', 'created_at']


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ['student', 'teacher', 'points', 'event_type', 'description', 'date', 'created_at']
    list_filter = ['event_type', 'teacher', 'date']
    search_fields = ['student__name', 'student__code', 'description']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
