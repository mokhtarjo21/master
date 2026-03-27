"""
Session Models
Session management with scheduling and repeat logic
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta, time
import uuid


class Session(models.Model):
    """
    Core Session model for classes
    """
    SESSION_STATUS = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    ]
    
    REPEAT_TYPES = [
        ('none', 'No Repeat'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, related_name='sessions')
    
    # Session Details
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Status & Progress
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='scheduled')
    actual_start_time = models.TimeField(blank=True, null=True)
    actual_end_time = models.TimeField(blank=True, null=True)
    
    # Repeat Configuration
    repeat_type = models.CharField(max_length=20, choices=REPEAT_TYPES, default='none')
    repeat_until = models.DateField(blank=True, null=True)
    repeat_count = models.PositiveIntegerField(blank=True, null=True)
    parent_session = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='repeated_sessions')
    
    # Content & Materials
    lesson_content = models.TextField(blank=True, null=True)
    homework_assigned = models.TextField(blank=True, null=True)
    materials_used = models.TextField(blank=True, null=True)
    
    # Attendance Summary
    total_students = models.PositiveIntegerField(default=0)
    present_count = models.PositiveIntegerField(default=0)
    absent_count = models.PositiveIntegerField(default=0)
    late_count = models.PositiveIntegerField(default=0)
    
    # System Fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sessions'
        indexes = [
            models.Index(fields=['group', 'date', 'is_active']),
            models.Index(fields=['date', 'start_time']),
            models.Index(fields=['status']),
            models.Index(fields=['repeat_type']),
        ]
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"{self.group.name} - {self.date} {self.start_time}"
    
    def save(self, *args, **kwargs):
        # Set title if not provided
        if not self.title:
            self.title = f"{self.group.name} Session"
        
        super().save(*args, **kwargs)
        
        # Create repeated sessions if this is a parent session
        if self.repeat_type != 'none' and not self.parent_session:
            self.create_repeated_sessions()
    
    def create_repeated_sessions(self):
        """Create repeated sessions based on repeat configuration"""
        if self.repeat_type == 'none':
            return
        
        current_date = self.date
        sessions_created = 0
        max_sessions = self.repeat_count or 52  # Default to 1 year
        
        while sessions_created < max_sessions:
            # Calculate next date
            if self.repeat_type == 'daily':
                current_date += timedelta(days=1)
            elif self.repeat_type == 'weekly':
                current_date += timedelta(weeks=1)
            elif self.repeat_type == 'biweekly':
                current_date += timedelta(weeks=2)
            elif self.repeat_type == 'monthly':
                # Add one month (approximate)
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
            
            # Check if we should stop
            if self.repeat_until and current_date > self.repeat_until:
                break
            
            # Create repeated session
            Session.objects.create(
                group=self.group,
                title=self.title,
                description=self.description,
                date=current_date,
                start_time=self.start_time,
                end_time=self.end_time,
                repeat_type='none',  # Repeated sessions don't repeat themselves
                parent_session=self,
                lesson_content=self.lesson_content,
                homework_assigned=self.homework_assigned,
                materials_used=self.materials_used,
                is_active=True
            )
            
            sessions_created += 1
    
    def update_attendance_summary(self):
        """Update attendance summary from attendance records"""
        from attendance.models import Attendance
        
        attendance_qs = Attendance.objects.filter(session=self)
        
        self.total_students = attendance_qs.count()
        self.present_count = attendance_qs.filter(status='present').count()
        self.absent_count = attendance_qs.filter(status='absent').count()
        self.late_count = attendance_qs.filter(status='late').count()
        
        self.save(update_fields=['total_students', 'present_count', 'absent_count', 'late_count'])
    
    def can_take_attendance(self):
        """Check if attendance can be taken for this session"""
        return self.status in ['scheduled', 'in_progress', 'completed']
    
    def start_session(self):
        """Mark session as started and auto-mark all students as absent"""
        if self.status == 'scheduled':
            self.status = 'in_progress'
            self.actual_start_time = timezone.now().time()
            self.save(update_fields=['status', 'actual_start_time'])
            
            # Auto-create absent records for all enrolled students
            self._initialize_attendance_as_absent()
    
    def _initialize_attendance_as_absent(self):
        """Create absent attendance records for all active students in the group"""
        from attendance.models import Attendance
        from students.models import StudentGroup
        
        # Get all active students in this group
        student_ids = StudentGroup.objects.filter(
            group=self.group,
            is_active=True
        ).values_list('student_id', flat=True)
        
        now = timezone.now()
        records_to_create = []
        
        for student_id in student_ids:
            # Only create if no record exists yet (don't overwrite existing)
            exists = Attendance.objects.filter(
                session=self,
                student_id=student_id
            ).exists()
            
            if not exists:
                records_to_create.append(
                    Attendance(
                        session=self,
                        student_id=student_id,
                        status='absent',
                        method='auto',
                        marked_at=now,
                    )
                )
        
        if records_to_create:
            Attendance.objects.bulk_create(records_to_create, ignore_conflicts=True)
            # Update the session attendance summary
            self.update_attendance_summary()
    
    def end_session(self):
        """Mark session as completed"""
        if self.status == 'in_progress':
            self.status = 'completed'
            self.actual_end_time = timezone.now().time()
            self.save(update_fields=['status', 'actual_end_time'])
    
    def cancel_session(self, reason=None):
        """Cancel session"""
        self.status = 'cancelled'
        if reason:
            self.description = f"Cancelled: {reason}"
        self.save(update_fields=['status', 'description'])


class SessionReminder(models.Model):
    """
    Session reminders for notifications
    """
    REMINDER_TYPES = [
        ('before_1h', '1 Hour Before'),
        ('before_30m', '30 Minutes Before'),
        ('before_15m', '15 Minutes Before'),
        ('at_start', 'At Session Start'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='reminders')
    
    # Reminder Configuration
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    reminder_time = models.DateTimeField()
    
    # Notification Details
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Status
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(blank=True, null=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'session_reminders'
        indexes = [
            models.Index(fields=['session', 'reminder_type']),
            models.Index(fields=['reminder_time', 'is_sent']),
        ]
    
    def __str__(self):
        return f"{self.session} - {self.get_reminder_type_display()}"


class SessionMaterial(models.Model):
    """
    Materials used in specific sessions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='session_materials')
    
    # Material Details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='session_materials/', blank=True, null=True)
    external_link = models.URLField(blank=True, null=True)
    
    # Usage Notes
    usage_notes = models.TextField(blank=True, null=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'session_materials'
        indexes = [
            models.Index(fields=['session']),
        ]
    
    def __str__(self):
        return f"{self.session} - {self.title}"


class SessionNote(models.Model):
    """
    Teacher notes for sessions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='notes')
    
    # Note Content
    title = models.CharField(max_length=200, blank=True, null=True)
    content = models.TextField()
    
    # Note Type
    note_type = models.CharField(max_length=50, choices=[
        ('general', 'General Note'),
        ('student_behavior', 'Student Behavior'),
        ('lesson_progress', 'Lesson Progress'),
        ('homework', 'Homework'),
        ('reminder', 'Reminder'),
    ], default='general')
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'session_notes'
        indexes = [
            models.Index(fields=['session', 'note_type']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.session} - {self.title or self.note_type}"