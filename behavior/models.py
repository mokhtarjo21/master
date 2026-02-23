"""
Behavior Assessment Models
Comprehensive student behavioral tracking system
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class BehaviorCategory(models.Model):
    """
    Configurable behavior categories per teacher
    Examples: Participation, Homework, Punctuality, Respect, Focus
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='behavior_categories'
    )

    name = models.CharField(max_length=100)            # e.g. "الالتزام بالواجب"
    name_en = models.CharField(max_length=100, blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)   # icon name for Flutter
    color = models.CharField(max_length=7, default='#4A90D9')       # hex color

    # Whether low ratings trigger a WhatsApp alert to the parent
    notify_on_negative = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'behavior_categories'
        unique_together = ['teacher', 'name']
        ordering = ['name']
        indexes = [
            models.Index(fields=['teacher', 'is_active']),
        ]

    def __str__(self):
        return f"{self.teacher.username} - {self.name}"


class BehaviorRecord(models.Model):
    """
    Individual behavioral assessment entry for a student
    """
    RATING_CHOICES = [
        ('excellent',         'ممتاز'),
        ('good',              'جيد'),
        ('satisfactory',      'مقبول'),
        ('needs_improvement', 'يحتاج تحسين'),
        ('poor',              'ضعيف'),
    ]

    RATING_SCORES = {
        'excellent': 5,
        'good': 4,
        'satisfactory': 3,
        'needs_improvement': 2,
        'poor': 1,
    }

    NEGATIVE_RATINGS = {'needs_improvement', 'poor'}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='behavior_records'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='behavior_records'
    )
    category = models.ForeignKey(
        BehaviorCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='records'
    )
    session = models.ForeignKey(
        'teaching_sessions.Session',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='behavior_records'
    )

    # Assessment
    rating = models.CharField(max_length=20, choices=RATING_CHOICES)
    score = models.PositiveSmallIntegerField(default=3)   # auto-set from rating
    notes = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.now)

    # Notification
    parent_notified = models.BooleanField(default=False)
    notified_at = models.DateTimeField(null=True, blank=True)

    # System
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_behavior_records'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'behavior_records'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['student', 'date']),
            models.Index(fields=['student', 'rating']),
            models.Index(fields=['teacher', 'date']),
            models.Index(fields=['category', 'date']),
            models.Index(fields=['session']),
        ]

    def __str__(self):
        return f"{self.student.name} — {self.get_rating_display()} ({self.date})"

    def save(self, *args, **kwargs):
        # Auto-set numeric score from rating
        self.score = self.RATING_SCORES.get(self.rating, 3)
        super().save(*args, **kwargs)

    @property
    def is_negative(self):
        return self.rating in self.NEGATIVE_RATINGS

    def notify_parent(self):
        """Create a WhatsApp notification to the parent."""
        if self.parent_notified:
            return False

        parent_link = self.student.parent_links.filter(
            is_active=True, is_primary_contact=True
        ).select_related('parent').first()

        phone = None
        if parent_link:
            phone = parent_link.parent.whatsapp_number or parent_link.parent.phone
        if not phone:
            phone = self.student.whatsapp_number or self.student.phone

        if not phone:
            return False

        from notifications.models import Notification

        category_name = self.category.name if self.category else 'السلوك العام'
        rating_display = self.get_rating_display()
        notes_part = f'\nملاحظة: {self.notes}' if self.notes else ''

        message = (
            f'تقييم سلوكي للطالب/ة: {self.student.name}\n'
            f'الجانب: {category_name}\n'
            f'التقييم: {rating_display}\n'
            f'التاريخ: {self.date}{notes_part}'
        )

        Notification.objects.create(
            teacher=self.teacher,
            recipient_type='parent' if parent_link else 'student',
            recipient_id=parent_link.parent.id if parent_link else self.student.id,
            recipient_name=parent_link.parent.name if parent_link else self.student.name,
            recipient_phone=phone,
            title=f'تقييم سلوكي — {self.student.name}',
            message=message,
            notification_type='alert',
            channel='whatsapp',
            status='pending',
            metadata={
                'behavior_record_id': str(self.id),
                'student_code': self.student.code,
            }
        )

        self.parent_notified = True
        self.notified_at = timezone.now()
        self.save(update_fields=['parent_notified', 'notified_at'])
        return True


class BehaviorSummary(models.Model):
    """
    Periodic summary of behavior scores for analytics
    """
    SUMMARY_TYPES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='behavior_summaries'
    )

    summary_type = models.CharField(max_length=10, choices=SUMMARY_TYPES)
    period_start = models.DateField()
    period_end = models.DateField()

    total_records = models.PositiveIntegerField(default=0)
    average_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    excellent_count = models.PositiveIntegerField(default=0)
    good_count = models.PositiveIntegerField(default=0)
    satisfactory_count = models.PositiveIntegerField(default=0)
    needs_improvement_count = models.PositiveIntegerField(default=0)
    poor_count = models.PositiveIntegerField(default=0)

    # JSON breakdown by category
    category_scores = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'behavior_summaries'
        unique_together = ['student', 'summary_type', 'period_start']
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['student', 'summary_type', 'period_start']),
        ]

    def __str__(self):
        return f"{self.student.name} — {self.summary_type} — {self.period_start}"

    def calculate(self):
        """Recalculate all summary fields from raw records."""
        from django.db.models import Avg, Count
        records = BehaviorRecord.objects.filter(
            student=self.student,
            date__gte=self.period_start,
            date__lte=self.period_end,
        )

        agg = records.aggregate(
            total=Count('id'),
            avg=Avg('score'),
            exc=Count('id', filter=models.Q(rating='excellent')),
            good=Count('id', filter=models.Q(rating='good')),
            sat=Count('id', filter=models.Q(rating='satisfactory')),
            ni=Count('id', filter=models.Q(rating='needs_improvement')),
            poor=Count('id', filter=models.Q(rating='poor')),
        )

        self.total_records = agg['total'] or 0
        self.average_score = agg['avg'] or 0
        self.excellent_count = agg['exc'] or 0
        self.good_count = agg['good'] or 0
        self.satisfactory_count = agg['sat'] or 0
        self.needs_improvement_count = agg['ni'] or 0
        self.poor_count = agg['poor'] or 0

        # Per-category breakdown
        cat_data = {}
        for rec in records.select_related('category'):
            cat_name = rec.category.name if rec.category else 'عام'
            if cat_name not in cat_data:
                cat_data[cat_name] = {'scores': [], 'count': 0}
            cat_data[cat_name]['scores'].append(rec.score)
            cat_data[cat_name]['count'] += 1

        self.category_scores = {
            cat: {
                'avg': round(sum(v['scores']) / len(v['scores']), 2),
                'count': v['count'],
            }
            for cat, v in cat_data.items()
        }
        self.save()
