"""
Teacher Models
Extended teacher profile and settings
"""
from django.db import models
from django.conf import settings
import uuid


class TeacherProfile(models.Model):
    """
    Extended teacher profile with additional settings
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='teacher_profile')
    
    # Business Information
    center_name = models.CharField(max_length=200)
    center_address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Subscription & Limits
    subscription_plan = models.CharField(max_length=50, default='free', choices=[
        ('free', 'Free Plan'),
        ('basic', 'Basic Plan'),
        ('premium', 'Premium Plan'),
        ('enterprise', 'Enterprise Plan'),
    ])
    max_students = models.PositiveIntegerField(default=50)
    max_groups = models.PositiveIntegerField(default=20)
    
    # Settings
    default_language = models.CharField(max_length=5, default='ar', choices=[
        ('ar', 'Arabic'),
        ('en', 'English')
    ])
    timezone = models.CharField(max_length=50, default='UTC')
    currency = models.CharField(max_length=3, default='SAR')
    
    # Financial Settings
    default_session_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    default_monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Notification Preferences
    email_notifications = models.BooleanField(default=True)
    whatsapp_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    
    # Smart Features
    smart_insights_enabled = models.BooleanField(default=True)
    auto_alerts_enabled = models.BooleanField(default=True)
    auto_receipts_enabled = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teacher_profiles'
        indexes = [
            models.Index(fields=['subscription_plan']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.center_name} - {self.user.username}"
    
    def can_add_student(self):
        """Check if teacher can add more students"""
        current_count = self.user.students.filter(is_active=True).count()
        return current_count < self.max_students
    
    def can_add_group(self):
        """Check if teacher can add more groups"""
        current_count = self.user.groups.filter(is_active=True).count()
        return current_count < self.max_groups


class TeacherStats(models.Model):
    """
    Daily/Monthly teacher statistics snapshot
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='teacher_stats')
    
    # Date for statistics
    date = models.DateField()
    stat_type = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
    ])
    
    # Student Statistics
    total_students = models.PositiveIntegerField(default=0)
    active_students = models.PositiveIntegerField(default=0)
    new_students = models.PositiveIntegerField(default=0)
    
    # Group Statistics
    total_groups = models.PositiveIntegerField(default=0)
    active_groups = models.PositiveIntegerField(default=0)
    
    # Session Statistics
    total_sessions = models.PositiveIntegerField(default=0)
    completed_sessions = models.PositiveIntegerField(default=0)
    cancelled_sessions = models.PositiveIntegerField(default=0)
    
    # Financial Statistics
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pending_payments = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    overdue_payments = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Attendance Statistics
    total_attendance = models.PositiveIntegerField(default=0)
    present_count = models.PositiveIntegerField(default=0)
    absent_count = models.PositiveIntegerField(default=0)
    late_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'teacher_stats'
        unique_together = ['teacher', 'date', 'stat_type']
        indexes = [
            models.Index(fields=['teacher', 'date', 'stat_type']),
            models.Index(fields=['date', 'stat_type']),
        ]
    
    def __str__(self):
        return f"{self.teacher.username} - {self.stat_type} - {self.date}"


class TeacherNotificationSettings(models.Model):
    """
    Detailed notification settings for teachers
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notification_settings'
    )
    
    # Payment Notifications
    payment_received_email = models.BooleanField(default=True)
    payment_received_whatsapp = models.BooleanField(default=True)
    payment_overdue_email = models.BooleanField(default=True)
    payment_overdue_whatsapp = models.BooleanField(default=True)
    
    # Session Notifications
    session_reminder_email = models.BooleanField(default=True)
    session_reminder_whatsapp = models.BooleanField(default=True)
    session_cancelled_email = models.BooleanField(default=True)
    session_cancelled_whatsapp = models.BooleanField(default=True)
    
    # Student Notifications
    new_student_email = models.BooleanField(default=True)
    student_absence_email = models.BooleanField(default=True)
    student_absence_whatsapp = models.BooleanField(default=True)
    
    # Smart Alert Notifications
    smart_alerts_email = models.BooleanField(default=True)
    smart_alerts_whatsapp = models.BooleanField(default=True)
    
    # System Notifications
    system_updates_email = models.BooleanField(default=True)
    backup_completion_email = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teacher_notification_settings'