"""
Exports Models
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class Export(models.Model):
    """Export job tracking"""
    EXPORT_TYPES = [
        ('students', 'Students Export'),
        ('payments', 'Payments Export'),
        ('attendance', 'Attendance Export'),
        ('grades', 'Grades Export'),
        ('groups', 'Groups Export'),
    ]
    
    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exports'
    )
    
    export_type = models.CharField(max_length=30, choices=EXPORT_TYPES)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # File
    file = models.FileField(upload_to='exports/', blank=True, null=True)
    file_size = models.IntegerField(default=0)  # in bytes
    records_count = models.IntegerField(default=0)
    
    # Filters
    filters = models.JSONField(default=dict, blank=True)
    fields = models.JSONField(default=list, blank=True)
    
    # Status
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    generated_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'exports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['teacher', 'export_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.export_type} - {self.format} - {self.status}"
