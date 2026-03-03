"""
Points & Rewards System
Gamification engine: earn points, redeem prizes, rank on leaderboard
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class PointRule(models.Model):
    """
    Teacher-defined rules that determine how many points are awarded/deducted
    for each event type.
    """
    EVENT_TYPES = [
        ('attendance',   'حضور'),
        ('grade',        'درجة امتحان'),
        ('homework',     'واجب'),
        ('dictation',    'إملاء'),
        ('absence',      'غياب'),
        ('late',         'تأخير'),
        ('bad_behavior', 'سلوك سيئ'),
        ('manual',       'يدوي'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='point_rules'
    )

    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    points = models.IntegerField(
        help_text='موجب للمكافأة، سالب للخصم'
    )
    description = models.CharField(max_length=255, blank=True, null=True)

    # Optional: only apply to a specific group
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='point_rules',
        help_text='اتركه فارغًا ليطبق على جميع المجموعات'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'point_rules'
        unique_together = ['teacher', 'event_type', 'group']
        ordering = ['event_type']
        indexes = [
            models.Index(fields=['teacher', 'is_active']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        sign = '+' if self.points >= 0 else ''
        return f"{self.get_event_type_display()} → {sign}{self.points} نقطة"


class Prize(models.Model):
    """
    Teacher-defined prizes unlocked at specific point thresholds.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prizes'
    )

    name = models.CharField(max_length=200)               # e.g. "شهادة تقدير"
    description = models.TextField(blank=True, null=True)
    points_required = models.PositiveIntegerField()       # e.g. 500
    icon = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=7, default='#FFD700')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'prizes'
        ordering = ['points_required']
        indexes = [
            models.Index(fields=['teacher', 'is_active', 'points_required']),
        ]

    def __str__(self):
        return f"{self.name} ({self.points_required} نقطة)"


class StudentPoints(models.Model):
    """
    Running total of points per student (per teacher scope).
    Automatically maintained by signals.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='point_balances'
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_point_balances'
    )

    total_points = models.IntegerField(default=0)
    total_earned = models.PositiveIntegerField(default=0)   # cumulative positive
    total_deducted = models.PositiveIntegerField(default=0) # cumulative negative (abs)

    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'student_points'
        unique_together = ['student', 'teacher']
        indexes = [
            models.Index(fields=['teacher', 'total_points']),
            models.Index(fields=['student']),
        ]

    def __str__(self):
        return f"{self.student.name} — {self.total_points} نقطة"

    def add_points(self, amount: int):
        """Add (positive) or deduct (negative) points and update totals."""
        self.total_points += amount
        if amount > 0:
            self.total_earned += amount
        else:
            self.total_deducted += abs(amount)
        self.save(update_fields=['total_points', 'total_earned', 'total_deducted', 'last_updated'])

    def get_next_prize(self, prizes_qs):
        """Return nearest prize not yet reached."""
        return prizes_qs.filter(
            points_required__gt=self.total_points,
            is_active=True
        ).order_by('points_required').first()

    def get_unlocked_prizes(self, prizes_qs):
        """Return all prizes the student has reached."""
        return prizes_qs.filter(
            points_required__lte=self.total_points,
            is_active=True
        )


class PointTransaction(models.Model):
    """
    Immutable log of every point event for a student.
    """
    EVENT_TYPES = PointRule.EVENT_TYPES  # reuse choices

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='point_transactions'
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='issued_point_transactions'
    )

    points = models.IntegerField()                      # +ve or -ve
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    description = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(default=timezone.now)

    # Optional references to source objects
    session = models.ForeignKey(
        'teaching_sessions.Session',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='point_transactions'
    )
    grade = models.ForeignKey(
        'grades.Grade',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='point_transactions'
    )
    behavior_record = models.ForeignKey(
        'behavior.BehaviorRecord',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='point_transactions'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'point_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'event_type', 'date']),
            models.Index(fields=['teacher', 'date']),
            models.Index(fields=['session']),
            models.Index(fields=['grade']),
            models.Index(fields=['behavior_record']),
        ]

    def __str__(self):
        sign = '+' if self.points >= 0 else ''
        return f"{self.student.name} — {sign}{self.points} ({self.get_event_type_display()})"
