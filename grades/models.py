"""
Grade Models
Comprehensive grade management with configurable types and analytics
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import date
import uuid


class GradeType(models.Model):
    """
    Configurable grade types (Quiz, Exam, Assignment, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='grade_types'
    )
    
    # Type Details
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    # Grading Configuration
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    min_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Weight in overall grade calculation
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    
    # Display Settings
    color = models.CharField(max_length=7, default='#007bff')  # Hex color
    icon = models.CharField(max_length=50, blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'grade_types'
        unique_together = ['teacher', 'name']
        indexes = [
            models.Index(fields=['teacher', 'is_active']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.teacher.username} - {self.name}"


class Grade(models.Model):
    """
    Core Grade model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='grades')
    grade_type = models.ForeignKey(GradeType, on_delete=models.CASCADE, related_name='grades')
    session = models.ForeignKey('teaching_sessions.Session', on_delete=models.SET_NULL, null=True, blank=True, related_name='grades')
    
    # Grade Details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Score
    score = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    
    # Calculated Fields
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    letter_grade = models.CharField(max_length=5, blank=True, null=True)
    
    # Date
    grade_date = models.DateField(default=date.today)
    
    # Additional Information
    notes = models.TextField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    
    # System Fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'grades'
        indexes = [
            models.Index(fields=['student', 'grade_type', 'is_active']),
            models.Index(fields=['grade_date', 'is_active']),
            models.Index(fields=['session', 'is_active']),
        ]
        ordering = ['-grade_date', '-created_at']
    
    def __str__(self):
        return f"{self.student.name} - {self.title} - {self.score}/{self.max_score}"
    
    def save(self, *args, **kwargs):
        # Calculate percentage
        if self.max_score > 0:
            self.percentage = (self.score / self.max_score) * 100
        else:
            self.percentage = 0
        
        # Calculate letter grade
        self.letter_grade = self.calculate_letter_grade()
        
        super().save(*args, **kwargs)
    
    def calculate_letter_grade(self):
        """Calculate letter grade based on percentage"""
        if self.percentage >= 90:
            return 'A+'
        elif self.percentage >= 85:
            return 'A'
        elif self.percentage >= 80:
            return 'B+'
        elif self.percentage >= 75:
            return 'B'
        elif self.percentage >= 70:
            return 'C+'
        elif self.percentage >= 65:
            return 'C'
        elif self.percentage >= 60:
            return 'D+'
        elif self.percentage >= 50:
            return 'D'
        else:
            return 'F'
    
    def get_grade_status(self):
        """Get grade status (Excellent, Good, etc.)"""
        if self.percentage >= 90:
            return 'Excellent'
        elif self.percentage >= 80:
            return 'Very Good'
        elif self.percentage >= 70:
            return 'Good'
        elif self.percentage >= 60:
            return 'Satisfactory'
        else:
            return 'Needs Improvement'


class GradeScale(models.Model):
    """
    Customizable grading scale for teachers
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='grade_scales'
    )
    
    # Scale Details
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    # Scale Configuration
    scale_data = models.JSONField(default=dict)  # Store scale ranges and letters
    
    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'grade_scales'
        indexes = [
            models.Index(fields=['teacher', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.teacher.username} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default scale per teacher
        if self.is_default:
            GradeScale.objects.filter(
                teacher=self.teacher,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        
        super().save(*args, **kwargs)


class GradeSummary(models.Model):
    """
    Grade summaries for students (monthly, term, etc.)
    """
    SUMMARY_TYPES = [
        ('monthly', 'Monthly'),
        ('term', 'Term'),
        ('semester', 'Semester'),
        ('yearly', 'Yearly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='grade_summaries')
    
    # Summary Period
    summary_type = models.CharField(max_length=20, choices=SUMMARY_TYPES)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Overall Statistics
    total_grades = models.PositiveIntegerField(default=0)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    average_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overall_letter_grade = models.CharField(max_length=5, blank=True, null=True)
    
    # Grade Type Breakdown
    grade_type_averages = models.JSONField(default=dict)  # Store averages by grade type
    
    # Rankings
    class_rank = models.PositiveIntegerField(blank=True, null=True)
    total_students = models.PositiveIntegerField(blank=True, null=True)
    
    # Trends
    improvement_trend = models.CharField(max_length=20, choices=[
        ('improving', 'Improving'),
        ('stable', 'Stable'),
        ('declining', 'Declining'),
    ], blank=True, null=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'grade_summaries'
        unique_together = ['student', 'summary_type', 'period_start', 'period_end']
        indexes = [
            models.Index(fields=['student', 'summary_type']),
            models.Index(fields=['period_start', 'period_end']),
        ]
    
    def __str__(self):
        return f"{self.student.name} - {self.summary_type} - {self.period_start}"
    
    def calculate_summary(self):
        """Calculate summary statistics"""
        grades = Grade.objects.filter(
            student=self.student,
            grade_date__gte=self.period_start,
            grade_date__lte=self.period_end,
            is_active=True,
            is_published=True
        )
        
        if not grades.exists():
            return
        
        # Basic statistics
        self.total_grades = grades.count()
        
        # Calculate weighted average if grade types have weights
        total_weighted_score = Decimal('0')
        total_weight = Decimal('0')
        
        grade_type_data = {}
        
        for grade in grades:
            weight = grade.grade_type.weight
            weighted_score = grade.percentage * weight
            
            total_weighted_score += weighted_score
            total_weight += weight
            
            # Track by grade type
            grade_type_name = grade.grade_type.name
            if grade_type_name not in grade_type_data:
                grade_type_data[grade_type_name] = {
                    'scores': [],
                    'weight': weight
                }
            grade_type_data[grade_type_name]['scores'].append(float(grade.percentage))
        
        # Calculate overall average
        if total_weight > 0:
            self.average_percentage = total_weighted_score / total_weight
        else:
            self.average_percentage = grades.aggregate(
                avg=models.Avg('percentage')
            )['avg'] or Decimal('0')
        
        # Calculate grade type averages
        for grade_type_name, data in grade_type_data.items():
            scores = data['scores']
            if scores:
                grade_type_data[grade_type_name]['average'] = sum(scores) / len(scores)
        
        self.grade_type_averages = grade_type_data
        
        # Calculate letter grade
        self.overall_letter_grade = self._calculate_letter_grade(self.average_percentage)
        
        self.save()
    
    def _calculate_letter_grade(self, percentage):
        """Calculate letter grade based on percentage"""
        if percentage >= 90:
            return 'A+'
        elif percentage >= 85:
            return 'A'
        elif percentage >= 80:
            return 'B+'
        elif percentage >= 75:
            return 'B'
        elif percentage >= 70:
            return 'C+'
        elif percentage >= 65:
            return 'C'
        elif percentage >= 60:
            return 'D+'
        elif percentage >= 50:
            return 'D'
        else:
            return 'F'


class GradeAlert(models.Model):
    """
    Alerts for grade-related issues
    """
    ALERT_TYPES = [
        ('low_grade', 'Low Grade'),
        ('failing_grade', 'Failing Grade'),
        ('grade_drop', 'Grade Drop'),
        ('missing_grades', 'Missing Grades'),
        ('improvement', 'Grade Improvement'),
    ]
    
    ALERT_SEVERITY = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='grade_alerts')
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    
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
        related_name='resolved_grade_alerts'
    )
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'grade_alerts'
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


class GradeComment(models.Model):
    """
    Comments and feedback on grades
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='comments')
    
    # Comment Details
    comment = models.TextField()
    is_private = models.BooleanField(default=False)  # Private comments not visible to students/parents
    
    # System Fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'grade_comments'
        indexes = [
            models.Index(fields=['grade', 'is_private']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.grade} - Comment by {self.created_by.username}"