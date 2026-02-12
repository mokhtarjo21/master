"""
Group Models
Class/Group management with different types and pricing
"""
from django.db import models
from django.conf import settings
from decimal import Decimal
import uuid


class Group(models.Model):
    """
    Core Group model for organizing students
    """
    GROUP_TYPES = [
        ('center', 'Center Class'),
        ('premium_center', 'Premium Center Class'),
        ('private', 'Private Class'),
        ('private_lesson', 'Private Lesson'),
        ('online', 'Online Class'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='teaching_groups'
    )
    
    # Basic Information
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    group_type = models.CharField(max_length=20, choices=GROUP_TYPES, default='center')
    subject = models.CharField(max_length=100, blank=True, null=True)
    grade_level = models.CharField(max_length=50, blank=True, null=True)
    
    # Capacity & Limits
    max_students = models.PositiveIntegerField(default=30)
    current_students_count = models.PositiveIntegerField(default=0)
    
    # Pricing
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    session_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    group_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    
    # Session Configuration
    sessions_per_month = models.PositiveIntegerField(default=8)
    session_duration_minutes = models.PositiveIntegerField(default=60)
    
    # Location & Setup
    classroom = models.CharField(max_length=100, blank=True, null=True)
    online_meeting_link = models.URLField(blank=True, null=True)
    meeting_password = models.CharField(max_length=50, blank=True, null=True)
    
    # Schedule Information
    schedule_notes = models.TextField(blank=True, null=True)
    
    # System Fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Soft Delete
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'groups'
        indexes = [
            models.Index(fields=['teacher', 'is_active']),
            models.Index(fields=['group_type']),
            models.Index(fields=['subject', 'grade_level']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.group_type})"
    
    def save(self, *args, **kwargs):
        # Update current students count
        if self.pk:
            self.current_students_count = self.group_students.filter(is_active=True).count()
        super().save(*args, **kwargs)
    
    def can_add_student(self):
        """Check if group can accept more students"""
        return self.current_students_count < self.max_students
    
    def get_active_students(self):
        """Get active students in this group"""
        from students.models import StudentGroup
        return StudentGroup.objects.filter(
            group=self,
            is_active=True
        ).select_related('student')
    
    def get_next_session(self):
        """Get next scheduled session"""
        from sessions.models import Session
        from django.utils import timezone
        
        return Session.objects.filter(
            group=self,
            date__gte=timezone.now().date(),
            is_active=True
        ).order_by('date', 'start_time').first()
    
    def get_monthly_revenue(self, year=None, month=None):
        """Calculate monthly revenue from this group"""
        from payments.models import Payment
        from django.utils import timezone
        
        if not year or not month:
            now = timezone.now()
            year = now.year
            month = now.month
        
        # Get all students in group
        student_ids = self.group_students.filter(is_active=True).values_list('student_id', flat=True)
        
        # Calculate revenue from monthly payments
        monthly_payments = Payment.objects.filter(
            student_id__in=student_ids,
            payment_type='monthly',
            status='paid',
            payment_date__year=year,
            payment_date__month=month
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        # Calculate revenue from session payments
        session_payments = Payment.objects.filter(
            student_id__in=student_ids,
            payment_type='session',
            status='paid',
            payment_date__year=year,
            payment_date__month=month
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        return monthly_payments + session_payments
    
    def get_attendance_rate(self, start_date=None, end_date=None):
        """Calculate group attendance rate"""
        from attendance.models import Attendance
        from django.db.models import Count, Q
        
        attendance_qs = Attendance.objects.filter(
            session__group=self
        )
        
        if start_date:
            attendance_qs = attendance_qs.filter(session__date__gte=start_date)
        if end_date:
            attendance_qs = attendance_qs.filter(session__date__lte=end_date)
        
        stats = attendance_qs.aggregate(
            total=Count('id'),
            present=Count('id', filter=Q(status__in=['present', 'late']))
        )
        
        if stats['total'] > 0:
            return round((stats['present'] / stats['total']) * 100, 2)
        return 0


class GroupSchedule(models.Model):
    """
    Weekly schedule for groups
    """
    WEEKDAYS = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='schedules')
    
    # Schedule Details
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Effective Period
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    
    # System Fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'group_schedules'
        indexes = [
            models.Index(fields=['group', 'weekday', 'is_active']),
            models.Index(fields=['effective_from', 'effective_until']),
        ]
    
    def __str__(self):
        weekday_name = dict(self.WEEKDAYS)[self.weekday]
        return f"{self.group.name} - {weekday_name} {self.start_time}-{self.end_time}"
    
    def is_currently_effective(self, date_obj=None):
        """Check if schedule is effective for given date"""
        from django.utils import timezone
        
        if not date_obj:
            date_obj = timezone.now().date()
        
        if date_obj < self.effective_from:
            return False
        
        if self.effective_until and date_obj > self.effective_until:
            return False
        
        return True


class GroupMaterial(models.Model):
    """
    Materials and resources for groups
    """
    MATERIAL_TYPES = [
        ('document', 'Document'),
        ('presentation', 'Presentation'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('link', 'External Link'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='materials')
    
    # Material Information
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPES, default='document')
    
    # File or Link
    file = models.FileField(upload_to='group_materials/', blank=True, null=True)
    external_link = models.URLField(blank=True, null=True)
    
    # Access Control
    is_public = models.BooleanField(default=False)  # Visible to students/parents
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'group_materials'
        indexes = [
            models.Index(fields=['group', 'is_public']),
            models.Index(fields=['material_type']),
        ]
    
    def __str__(self):
        return f"{self.group.name} - {self.title}"


class GroupAnnouncement(models.Model):
    """
    Announcements for groups
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='announcements')
    
    # Announcement Content
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # Visibility & Notifications
    is_urgent = models.BooleanField(default=False)
    send_notification = models.BooleanField(default=True)
    
    # Scheduling
    publish_at = models.DateTimeField()
    expire_at = models.DateTimeField(null=True, blank=True)
    
    # System Fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'group_announcements'
        indexes = [
            models.Index(fields=['group', 'is_active']),
            models.Index(fields=['publish_at', 'expire_at']),
            models.Index(fields=['is_urgent']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.group.name} - {self.title}"
    
    def is_currently_published(self):
        """Check if announcement is currently published"""
        from django.utils import timezone
        now = timezone.now()
        
        if now < self.publish_at:
            return False
        
        if self.expire_at and now > self.expire_at:
            return False
        
        return self.is_active