"""
Smart Insights Models
Analytics, suggestions, and intelligence engine
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid


class Insight(models.Model):
    """
    Smart insights and suggestions
    """
    INSIGHT_CATEGORIES = [
        ('financial', 'Financial'),
        ('attendance', 'Attendance'),
        ('performance', 'Performance'),
        ('engagement', 'Engagement'),
        ('operational', 'Operational'),
        ('growth', 'Growth'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='insights'
    )
    
    # Insight Details
    category = models.CharField(max_length=20, choices=INSIGHT_CATEGORIES)
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='medium')
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Insight Data
    insight_data = models.JSONField(default=dict)  # Store analysis results
    recommendations = models.JSONField(default=list)  # List of recommended actions
    
    # Status
    is_active = models.BooleanField(default=True)
    action_taken = models.BooleanField(default=False)
    action_notes = models.TextField(blank=True, null=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'insights'
        indexes = [
            models.Index(fields=['teacher', 'category', 'is_active']),
            models.Index(fields=['priority', 'is_active']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.teacher.username} - {self.title}"
    
    def mark_action_taken(self, notes=''):
        """Mark insight as acted upon"""
        self.action_taken = True
        self.action_notes = notes
        self.save(update_fields=['action_taken', 'action_notes'])


class Alert(models.Model):
    """
    System alerts and warnings
    """
    ALERT_TYPES = [
        ('low_attendance', 'Low Attendance'),
        ('payment_overdue', 'Payment Overdue'),
        ('session_cancelled', 'Session Cancelled'),
        ('student_inactive', 'Student Inactive'),
        ('grade_drop', 'Grade Drop'),
        ('capacity_full', 'Capacity Full'),
        ('system_error', 'System Error'),
        ('data_sync', 'Data Sync Issue'),
    ]
    
    SEVERITY_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    
    # Alert Details
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='warning')
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Target Information
    target_type = models.CharField(max_length=20, blank=True, null=True)  # student, group, session, etc.
    target_id = models.UUIDField(blank=True, null=True)
    target_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Alert Data
    trigger_data = models.JSONField(default=dict)  # Data that triggered the alert
    suggested_actions = models.JSONField(default=list)  # Suggested actions
    
    # Status
    is_active = models.BooleanField(default=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts'
    )
    resolution_notes = models.TextField(blank=True, null=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'alerts'
        indexes = [
            models.Index(fields=['teacher', 'alert_type', 'is_active']),
            models.Index(fields=['severity', 'is_active']),
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.teacher.username} - {self.title}"
    
    def resolve(self, resolved_by=None, notes=''):
        """Mark alert as resolved"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = resolved_by
        self.resolution_notes = notes
        self.save(update_fields=['is_resolved', 'resolved_at', 'resolved_by', 'resolution_notes'])


class Suggestion(models.Model):
    """
    AI-powered suggestions for improvement
    """
    SUGGESTION_CATEGORIES = [
        ('financial', 'Financial Optimization'),
        ('scheduling', 'Schedule Optimization'),
        ('engagement', 'Student Engagement'),
        ('retention', 'Student Retention'),
        ('growth', 'Business Growth'),
        ('efficiency', 'Operational Efficiency'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='suggestions'
    )
    
    # Suggestion Details
    category = models.CharField(max_length=20, choices=SUGGESTION_CATEGORIES)
    priority = models.CharField(max_length=20, choices=Insight.PRIORITY_LEVELS, default='medium')
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Implementation Details
    implementation_steps = models.JSONField(default=list)
    expected_impact = models.TextField(blank=True, null=True)
    effort_level = models.CharField(max_length=20, choices=[
        ('low', 'Low Effort'),
        ('medium', 'Medium Effort'),
        ('high', 'High Effort'),
    ], default='medium')
    
    # Supporting Data
    analysis_data = models.JSONField(default=dict)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_implemented = models.BooleanField(default=False)
    implementation_date = models.DateTimeField(blank=True, null=True)
    implementation_notes = models.TextField(blank=True, null=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'suggestions'
        indexes = [
            models.Index(fields=['teacher', 'category', 'is_active']),
            models.Index(fields=['priority', 'is_active']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.teacher.username} - {self.title}"
    
    def mark_implemented(self, notes=''):
        """Mark suggestion as implemented"""
        self.is_implemented = True
        self.implementation_date = timezone.now()
        self.implementation_notes = notes
        self.save(update_fields=['is_implemented', 'implementation_date', 'implementation_notes'])


class AnalyticsSnapshot(models.Model):
    """
    Periodic analytics snapshots for trend analysis
    """
    SNAPSHOT_TYPES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='analytics_snapshots'
    )
    
    # Snapshot Details
    snapshot_type = models.CharField(max_length=20, choices=SNAPSHOT_TYPES)
    snapshot_date = models.DateField()
    
    # Student Metrics
    total_students = models.PositiveIntegerField(default=0)
    active_students = models.PositiveIntegerField(default=0)
    new_students = models.PositiveIntegerField(default=0)
    churned_students = models.PositiveIntegerField(default=0)
    
    # Financial Metrics
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pending_payments = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    overdue_payments = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Attendance Metrics
    total_sessions = models.PositiveIntegerField(default=0)
    attendance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    punctuality_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Performance Metrics
    average_grade = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    grade_improvement = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Engagement Metrics
    notification_open_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    parent_engagement_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Additional Metrics
    metrics_data = models.JSONField(default=dict)  # Store additional calculated metrics
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'analytics_snapshots'
        unique_together = ['teacher', 'snapshot_type', 'snapshot_date']
        indexes = [
            models.Index(fields=['teacher', 'snapshot_type', 'snapshot_date']),
            models.Index(fields=['snapshot_date']),
        ]
        ordering = ['-snapshot_date']
    
    def __str__(self):
        return f"{self.teacher.username} - {self.snapshot_type} - {self.snapshot_date}"


class DashboardWidget(models.Model):
    """
    Customizable dashboard widgets
    """
    WIDGET_TYPES = [
        ('chart', 'Chart'),
        ('metric', 'Metric'),
        ('list', 'List'),
        ('calendar', 'Calendar'),
        ('progress', 'Progress'),
        ('alert', 'Alert'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dashboard_widgets'
    )
    
    # Widget Details
    title = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    description = models.TextField(blank=True, null=True)
    
    # Configuration
    config = models.JSONField(default=dict)  # Widget-specific configuration
    data_source = models.CharField(max_length=50)  # Data source identifier
    refresh_interval = models.PositiveIntegerField(default=300)  # Seconds
    
    # Layout
    position_x = models.PositiveIntegerField(default=0)
    position_y = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=1)
    height = models.PositiveIntegerField(default=1)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'dashboard_widgets'
        indexes = [
            models.Index(fields=['teacher', 'is_active']),
            models.Index(fields=['widget_type']),
        ]
        ordering = ['position_y', 'position_x']
    
    def __str__(self):
        return f"{self.teacher.username} - {self.title}"