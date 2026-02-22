"""
User Authentication Models
Supports Teacher, Student, and Parent user types with appropriate authentication methods
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
import uuid


class User(AbstractUser):
    """
    Extended User model supporting multiple authentication types
    """
    USER_TYPES = [
        ('admin', 'Administrator'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    language = models.CharField(max_length=5, default='ar', choices=[('ar', 'Arabic'), ('en', 'English')])
    last_activity = models.DateTimeField(auto_now=True)
    is_active_session = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Teacher-specific fields
    teacher_pin = models.CharField(max_length=255, blank=True, null=True)
    center_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Student/Parent-specific fields
    student_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    access_token = models.CharField(max_length=255, blank=True, null=True)
    qr_token = models.CharField(max_length=255, blank=True, null=True)
    qr_expires_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['student_code']),
            models.Index(fields=['qr_token']),
            models.Index(fields=['last_activity']),
        ]
    
    def set_teacher_pin(self, raw_pin):
        """Set hashed PIN for teacher authentication"""
        self.teacher_pin = make_password(raw_pin)
        
    def check_teacher_pin(self, raw_pin):
        """Check teacher PIN"""
        if not self.teacher_pin:
            return False
        return check_password(raw_pin, self.teacher_pin)
    
    def generate_student_code(self):
        """Generate unique student code"""
        import random
        import string
        
        while True:
            code = 'ST-' + ''.join(random.choices(string.digits, k=7))
            if not User.objects.filter(student_code=code).exists():
                self.student_code = code
                break
    
    def generate_qr_token(self):
        """Generate QR access token with expiry"""
        import secrets
        self.qr_token = secrets.token_urlsafe(32)
        self.qr_expires_at = timezone.now() + timezone.timedelta(seconds=300)  # 5 minutes
    
    def is_qr_token_valid(self):
        """Check if QR token is still valid"""
        if not self.qr_token or not self.qr_expires_at:
            return False
        return timezone.now() < self.qr_expires_at


class TeacherSession(models.Model):
    """
    Teacher session management for PIN-based authentication
    """
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teacher_sessions')
    session_token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    device_info = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'teacher_sessions'
        indexes = [
            models.Index(fields=['session_token']),
            models.Index(fields=['expires_at']),
        ]
    
    def is_expired(self):
        return timezone.now() > self.expires_at


class StudentAccessLog(models.Model):
    """
    Log student/parent access attempts and successful logins
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='access_logs')
    access_method = models.CharField(max_length=20, choices=[
        ('code', 'Student Code'),
        ('token', 'Access Token'),
        ('qr', 'QR Code'),
    ])
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    success = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'student_access_logs'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['success', 'created_at']),
        ]