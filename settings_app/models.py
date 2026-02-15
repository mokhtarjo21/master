"""
Settings App Models
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class AppSettings(models.Model):
    """Application settings per teacher"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='app_settings'
    )
    
    # App Identity
    center_name = models.CharField(max_length=200, default='My Learning Center')
    teacher_name = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    
    # Preferences
    language = models.CharField(max_length=5, choices=[('ar', 'Arabic'), ('en', 'English')], default='ar')
    theme = models.CharField(max_length=10, choices=[('light', 'Light'), ('dark', 'Dark')], default='light')
    currency = models.CharField(max_length=3, default='SAR')
    timezone = models.CharField(max_length=50, default='Asia/Riyadh')
    
    # Notifications
    email_enabled = models.BooleanField(default=True)
    whatsapp_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    
    # Smart Alerts
    attendance_alerts = models.BooleanField(default=True)
    payment_alerts = models.BooleanField(default=True)
    grade_alerts = models.BooleanField(default=True)
    
    # Alert Thresholds
    
    # Alert Thresholds
    low_attendance_rate = models.IntegerField(default=70)
    consecutive_absences = models.IntegerField(default=3)
    overdue_payment_days = models.IntegerField(default=7)
    low_grade_threshold = models.IntegerField(default=60)
    
    # Security Settings
    two_factor_enabled = models.BooleanField(default=False, help_text="Enable two-factor authentication")
    session_timeout_minutes = models.IntegerField(default=60, help_text="Session timeout in minutes")
    auto_logout_enabled = models.BooleanField(default=True, help_text="Auto logout after timeout")
    require_pin_for_danger_zone = models.BooleanField(default=True, help_text="Require PIN for dangerous operations")
    
    # Session Defaults
    default_session_duration = models.IntegerField(default=60, help_text="Default session duration in minutes")
    working_hours_start = models.TimeField(default='08:00', help_text="Start of working hours")
    working_hours_end = models.TimeField(default='20:00', help_text="End of working hours")
    weekend_days = models.CharField(max_length=20, default='FRI,SAT', help_text="Weekend days (comma-separated)")
    
    # Notification Advanced Settings
    notification_quiet_start = models.TimeField(null=True, blank=True, help_text="Start of quiet hours")
    notification_quiet_end = models.TimeField(null=True, blank=True, help_text="End of quiet hours")
    digest_notifications = models.BooleanField(default=False, help_text="Send digest instead of realtime")
    digest_frequency = models.CharField(
        max_length=10, 
        choices=[('daily', 'Daily'), ('weekly', 'Weekly')],
        default='daily',
        help_text="Frequency of digest notifications"
    )
    
    # System
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'app_settings'
        verbose_name_plural = 'App Settings'
    
    def __str__(self):
        return f"Settings for {self.teacher.username}"


class DangerZoneAction(models.Model):
    """Log of dangerous operations"""
    RESET_TYPES = [
        ('delete_students', 'Delete All Students'),
        ('delete_sessions', 'Delete All Sessions'),
        ('delete_payments', 'Delete All Payments'),
        ('delete_grades', 'Delete All Grades'),
        ('delete_all', 'Delete ALL Data'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='danger_zone_actions'
    )
    
    action_type = models.CharField(max_length=30, choices=RESET_TYPES)
    confirmation_text = models.CharField(max_length=200)
    items_affected = models.IntegerField(default=0)
    
    executed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'danger_zone_actions'
        ordering = ['-executed_at']
    
    def __str__(self):
        return f"{self.action_type} by {self.teacher.username}"
