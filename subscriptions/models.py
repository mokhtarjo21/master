"""
Subscriptions Models
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class SubscriptionPlan(models.Model):
    """Available subscription plans"""
    BILLING_CYCLES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=50)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLES, default='monthly')
    
    # Limits
    max_students = models.IntegerField(default=20)
    max_groups = models.IntegerField(default=5)
    storage_gb = models.IntegerField(default=1)
    
    # Features
    features = models.JSONField(default=list)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscription_plans'
        ordering = ['price']
    
    def __str__(self):
        return f"{self.name} - {self.price} {self.billing_cycle}"


class TeacherSubscription(models.Model):
    """Teacher's current subscription"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('trial', 'Trial'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    auto_renew = models.BooleanField(default=True)
    
    # Usage tracking
    current_students = models.IntegerField(default=0)
    current_groups = models.IntegerField(default=0)
    storage_used_gb = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teacher_subscriptions'
    
    def __str__(self):
        return f"{self.teacher.username} - {self.plan.name}"
    
    def is_expired(self):
        if self.end_date:
            return timezone.now().date() > self.end_date
        return False
    
    def update_usage(self):
        """Update current usage statistics"""
        from students.models import Student
        from groups.models import Group
        
        self.current_students = Student.objects.filter(teacher=self.teacher, is_active=True).count()
        self.current_groups = Group.objects.filter(teacher=self.teacher, is_active=True).count()
        self.save(update_fields=['current_students', 'current_groups'])
