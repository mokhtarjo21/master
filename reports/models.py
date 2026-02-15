"""
Reports Models
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class Report(models.Model):
    """Generated reports"""
    REPORT_TYPES = [
        ('student_report', 'Student Report'),
        ('monthly_financial', 'Monthly Financial Report'),
        ('attendance_report', 'Attendance Report'),
        ('payment_report', 'Payment Report'),
        ('grade_report', 'Grade Report'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('json', 'JSON'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    
    # Report Details
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Period
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)
    
    # File
    file = models.FileField(upload_to='reports/', blank=True, null=True)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='pdf')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    
    # Metadata
    filters = models.JSONField(default=dict, blank=True)
    options = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    generated_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['teacher', 'report_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.status}"


class ReportTemplate(models.Model):
    """Custom report templates"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='report_templates'
    )
    
    name = models.CharField(max_length=100)
    report_type = models.CharField(max_length=30, choices=Report.REPORT_TYPES)
    template_config = models.JSONField(default=dict)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'report_templates'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.report_type})"
