"""
Receipt Admin Configuration
"""
from django.contrib import admin
from .models import Receipt, ReceiptTemplate, ReceiptItem, ReceiptLog, ReceiptBatch


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = [
        'receipt_number', 'payment', 'receipt_type', 'status',
        'pdf_generated_at', 'sent_at', 'created_at'
    ]
    list_filter = ['status', 'receipt_type', 'created_at', 'pdf_generated_at']
    search_fields = ['receipt_number', 'payment__student__name', 'title']
    readonly_fields = [
        'receipt_number', 'pdf_generated_at', 'sent_at',
        'error_message', 'retry_count', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('payment', 'receipt_number', 'receipt_type', 'status')
        }),
        ('Content', {
            'fields': ('title', 'description')
        }),
        ('PDF Generation', {
            'fields': ('pdf_file', 'pdf_generated_at', 'error_message', 'retry_count')
        }),
        ('Sending', {
            'fields': ('sent_at', 'sent_to', 'sent_via_whatsapp')
        }),
        ('System', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(ReceiptTemplate)
class ReceiptTemplateAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'name', 'template_type', 'is_active', 'is_default']
    list_filter = ['template_type', 'is_active', 'is_default', 'language']
    search_fields = ['teacher__username', 'name']


@admin.register(ReceiptItem)
class ReceiptItemAdmin(admin.ModelAdmin):
    list_display = ['receipt', 'description', 'quantity', 'unit_price', 'total_price']
    list_filter = ['created_at']
    search_fields = ['receipt__receipt_number', 'description']


@admin.register(ReceiptLog)
class ReceiptLogAdmin(admin.ModelAdmin):
    list_display = ['receipt', 'action', 'success', 'performed_by', 'created_at']
    list_filter = ['action', 'success', 'created_at']
    search_fields = ['receipt__receipt_number', 'details']
    readonly_fields = ['created_at']


@admin.register(ReceiptBatch)
class ReceiptBatchAdmin(admin.ModelAdmin):
    list_display = [
        'teacher', 'name', 'status', 'total_receipts',
        'processed_receipts', 'failed_receipts', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['teacher__username', 'name']
    readonly_fields = [
        'total_receipts', 'processed_receipts', 'failed_receipts',
        'started_at', 'completed_at', 'created_at'
    ]