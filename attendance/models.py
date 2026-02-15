"""
Attendance Models
Comprehensive attendance tracking with multiple methods
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class Attendance(models.Model):
    """
    Core Attendance model
    """
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused Absence'),
    ]
    
    ATTENDANCE_METHOD = [
        ('manual', 'Manual Entry'),
        ('qr_code', 'QR Code Scan'),
        ('bulk', 'Bulk Entry'),
        ('auto', 'Automatic'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey('teaching_sessions.Session', on_delete=models.CASCADE, related_name='attendance_records')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='attendance_records')
    
    # Attendance Details
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='present')
    method = models.CharField(max_length=20, choices=ATTENDANCE_METHOD, default='manual')
    
    # Timing
    marked_at = models.DateTimeField(default=timezone.now)
    arrival_time = models.TimeField(blank=True, null=True)
    
    # Additional Information
    notes = models.TextField(blank=True, null=True)
    excuse_reason = models.TextField(blank=True, null=True)
    
    # QR Code specific
    qr_token = models.CharField(max_length=255, blank=True, null=True)
    
    # System Fields
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='marked_attendance'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'attendance'
        unique_together = ['session', 'student']
        indexes = [
            models.Index(fields=['session', 'status']),
            models.Index(fields=['student', 'status']),
            models.Index(fields=['marked_at']),
            models.Index(fields=['qr_token']),
        ]
        ordering = ['-marked_at']
    
    def __str__(self):
        return f"{self.student.name} - {self.session} - {self.status}"
    
    def save(self, *args, **kwargs):
        # Set arrival time if not provided and status is present/late
        if not self.arrival_time and self.status in ['present', 'late']:
            self.arrival_time = timezone.now().time()
        
        # Determine if late based on session start time
        if self.status == 'present' and self.arrival_time and self.session.start_time:
            if self.arrival_time > self.session.start_time:
                self.status = 'late'
        
        super().save(*args, **kwargs)
        
        # Update session attendance summary
        self.session.update_attendance_summary()
        
        # Update student remaining sessions if per-session subscription
        if self.student.subscription_type == 'per_session' and self.status in ['present', 'late']:
            self.student.update_remaining_sessions()
    
    def is_late(self):
        """Check if attendance is marked as late"""
        return self.status == 'late'
    
    def is_present(self):
        """Check if student was present (including late)"""
        return self.status in ['present', 'late']


class AttendanceQRCode(models.Model):
    """
    QR codes for attendance marking
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey('teaching_sessions.Session', on_delete=models.CASCADE, related_name='qr_codes')
    
    # QR Code Details
    qr_token = models.CharField(max_length=255, unique=True)
    qr_data = models.TextField()  # JSON data for QR code
    
    # Validity
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Usage Tracking
    scan_count = models.PositiveIntegerField(default=0)
    max_scans = models.PositiveIntegerField(default=100)
    
    # System Fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='created_qr_codes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'attendance_qr_codes'
        indexes = [
            models.Index(fields=['qr_token']),
            models.Index(fields=['session', 'is_active']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]
    
    def __str__(self):
        return f"QR Code for {self.session}"
    
    def is_valid(self):
        """Check if QR code is currently valid"""
        now = timezone.now()
        return (
            self.is_active and 
            self.valid_from <= now <= self.valid_until and
            self.scan_count < self.max_scans
        )
    
    def increment_scan_count(self):
        """Increment scan count"""
        self.scan_count += 1
        self.save(update_fields=['scan_count'])


class AttendanceSummary(models.Model):
    """
    Daily/Monthly attendance summaries for students
    """
    SUMMARY_TYPES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='attendance_summaries')
    
    # Summary Period
    summary_type = models.CharField(max_length=20, choices=SUMMARY_TYPES)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Attendance Counts
    total_sessions = models.PositiveIntegerField(default=0)
    present_count = models.PositiveIntegerField(default=0)
    absent_count = models.PositiveIntegerField(default=0)
    late_count = models.PositiveIntegerField(default=0)
    excused_count = models.PositiveIntegerField(default=0)
    
    # Calculated Fields
    attendance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    punctuality_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'attendance_summaries'
        unique_together = ['student', 'summary_type', 'period_start', 'period_end']
        indexes = [
            models.Index(fields=['student', 'summary_type']),
            models.Index(fields=['period_start', 'period_end']),
        ]
    
    def __str__(self):
        return f"{self.student.name} - {self.summary_type} - {self.period_start}"
    
    def calculate_rates(self):
        """Calculate attendance and punctuality rates"""
        if self.total_sessions > 0:
            # Attendance rate (present + late + excused) / total
            attended = self.present_count + self.late_count + self.excused_count
            self.attendance_rate = (attended / self.total_sessions) * 100
            
            # Punctuality rate (present only) / total attended
            if attended > 0:
                self.punctuality_rate = (self.present_count / attended) * 100
            else:
                self.punctuality_rate = 0
        else:
            self.attendance_rate = 0
            self.punctuality_rate = 0
        
        self.save(update_fields=['attendance_rate', 'punctuality_rate'])


class AttendanceAlert(models.Model):
    """
    Alerts for attendance issues
    """
    ALERT_TYPES = [
        ('consecutive_absence', 'Consecutive Absences'),
        ('low_attendance', 'Low Attendance Rate'),
        ('frequent_lateness', 'Frequent Lateness'),
        ('no_attendance_marked', 'No Attendance Marked'),
    ]
    
    ALERT_SEVERITY = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='attendance_alerts')
    
    # Alert Details
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=ALERT_SEVERITY, default='medium')
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Alert Data
    trigger_data = models.JSONField(default=dict)  # Store specific data that triggered the alert
    
    # Status
    is_active = models.BooleanField(default=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_attendance_alerts'
    )
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'attendance_alerts'
        indexes = [
            models.Index(fields=['student', 'alert_type', 'is_active']),
            models.Index(fields=['severity', 'is_active']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.name} - {self.title}"
    
    def resolve(self, resolved_by=None):
        """Mark alert as resolved"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = resolved_by
        self.save(update_fields=['is_resolved', 'resolved_at', 'resolved_by'])