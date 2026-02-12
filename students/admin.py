"""
Student Admin Configuration
"""
from django.contrib import admin
from .models import Student, Parent, StudentParentLink, StudentGroup


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'teacher', 'subscription_type', 
        'subscription_status', 'remaining_sessions', 'remaining_amount', 'is_active'
    ]
    list_filter = [
        'subscription_type', 'subscription_status', 'is_active', 
        'teacher', 'registration_date'
    ]
    search_fields = ['name', 'code', 'phone', 'email']
    readonly_fields = ['code', 'total_paid', 'remaining_amount', 'registration_date', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'teacher', 'phone', 'whatsapp_number', 'email', 'date_of_birth', 'address')
        }),
        ('Subscription', {
            'fields': ('subscription_type', 'subscription_status', 'monthly_price', 'per_session_price', 'student_discount')
        }),
        ('Sessions & Payments', {
            'fields': ('remaining_sessions', 'total_sessions_bought', 'total_paid', 'remaining_amount')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone')
        }),
        ('System', {
            'fields': ('is_active', 'registration_date', 'notes', 'created_at', 'updated_at')
        })
    )


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ['name', 'teacher', 'phone', 'relationship', 'is_active']
    list_filter = ['relationship', 'is_active', 'teacher']
    search_fields = ['name', 'phone', 'email']


@admin.register(StudentParentLink)
class StudentParentLinkAdmin(admin.ModelAdmin):
    list_display = ['student', 'parent', 'is_primary_contact', 'can_receive_notifications', 'is_active']
    list_filter = ['is_primary_contact', 'can_receive_notifications', 'is_active']
    search_fields = ['student__name', 'parent__name']


@admin.register(StudentGroup)
class StudentGroupAdmin(admin.ModelAdmin):
    list_display = ['student', 'group', 'enrollment_date', 'is_active']
    list_filter = ['is_active', 'enrollment_date',]
    search_fields = ['student__name', 'group__name']