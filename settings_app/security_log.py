"""
Security Log Model
Track security-related events for audit purposes
"""
from django.db import models
from django.conf import settings
import uuid


class SecurityLog(models.Model):
    """Security event logging"""
    EVENT_TYPES = [
        ('pin_change', 'PIN Changed'),
        ('pin_change_failed', 'PIN Change Failed'),
        ('login_failed', 'Failed Login'),
        ('data_export', 'Data Exported'),
        ('settings_changed', 'Settings Changed'),
        ('danger_zone_action', 'Danger Zone Action'),
        ('two_factor_enabled', 'Two-Factor Enabled'),
        ('two_factor_disabled', 'Two-Factor Disabled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='security_logs'
    )
    
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'security_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['teacher', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.teacher.username} at {self.created_at}"
