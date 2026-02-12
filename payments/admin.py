"""
Payment Admin Configuration
"""
from django.contrib import admin
from .models import Payment, PaymentTransaction, PaymentPlan, PaymentReminder, PaymentMethod


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'payment_type', 'amount', 'amount_paid', 
        'remaining_amount', 'status', 'due_date', 'payment_date'
    ]
    list_filter = ['status', 'payment_type', 'payment_method', 'due_date', 'created_at']
    search_fields = ['student__name', 'student__code', 'reference_number']
    readonly_fields = ['remaining_amount', 'reference_number', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('student', 'payment_type', 'amount', 'amount_paid', 'remaining_amount')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'status', 'due_date', 'payment_date')
        }),
        ('Period', {
            'fields': ('period_start', 'period_end')
        }),
        ('Reference', {
            'fields': ('reference_number', 'transaction_id')
        }),
        ('Discount', {
            'fields': ('discount_amount', 'discount_reason')
        }),
        ('Notes', {
            'fields': ('notes', 'internal_notes')
        }),
        ('System', {
            'fields': ('created_by', 'is_active', 'created_at', 'updated_at')
        })
    )


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['payment', 'amount', 'payment_method', 'transaction_date', 'created_at']
    list_filter = ['payment_method', 'transaction_date', 'created_at']
    search_fields = ['payment__student__name', 'transaction_reference', 'receipt_number']
    readonly_fields = ['created_at']


@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'total_amount', 'installment_amount', 
        'number_of_installments', 'installments_paid', 'status'
    ]
    list_filter = ['status', 'installment_frequency', 'start_date']
    search_fields = ['student__name', 'description']
    readonly_fields = ['installments_paid', 'amount_paid', 'created_at', 'updated_at']


@admin.register(PaymentReminder)
class PaymentReminderAdmin(admin.ModelAdmin):
    list_display = ['payment', 'reminder_type', 'reminder_date', 'is_sent', 'sent_at']
    list_filter = ['reminder_type', 'is_sent', 'reminder_date']
    search_fields = ['payment__student__name', 'title']
    readonly_fields = ['sent_at', 'created_at']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'name', 'method_type', 'is_active', 'is_default']
    list_filter = ['method_type', 'is_active', 'is_default']
    search_fields = ['teacher__username', 'name']