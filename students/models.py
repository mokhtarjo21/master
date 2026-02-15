"""
Student Models
Core student management with subscription logic
"""
from django.db import models
from django.conf import settings
from decimal import Decimal
import uuid


class Student(models.Model):
    """
    Core Student model with subscription and financial logic
    """
    SUBSCRIPTION_TYPES = [
        ('monthly', 'Monthly Subscription'),
        ('per_session', 'Per Session'),
        ('free', 'Free Student'),
    ]
    
    SUBSCRIPTION_STATUS = [
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='students'
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='student_profile'
    )
    
    # Basic Information
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)  # ST-XXXXXXX format
    phone = models.CharField(max_length=20, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Subscription & Financial
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPES, default='monthly')
    subscription_status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS, default='active')
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    per_session_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    student_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    
    # Session Tracking
    remaining_sessions = models.PositiveIntegerField(default=0)
    total_sessions_bought = models.PositiveIntegerField(default=0)
    
    # Financial Tracking
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=200, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # System Fields
    is_active = models.BooleanField(default=True)
    registration_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Soft Delete
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'students'
        indexes = [
            models.Index(fields=['teacher', 'is_active']),
            models.Index(fields=['code']),
            models.Index(fields=['subscription_status']),
            models.Index(fields=['registration_date']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def save(self, *args, **kwargs):
        # Generate student code if not provided
        if not self.code:
            self.generate_code()
        
        # Create user account if not exists
        if not self.user and self.teacher:
            self.create_user_account()
        
        super().save(*args, **kwargs)
    
    def generate_code(self):
        """Generate unique student code"""
        import random
        import string
        
        while True:
            code = 'ST-' + ''.join(random.choices(string.digits, k=7))
            if not Student.objects.filter(code=code).exists():
                self.code = code
                break
    
    def create_user_account(self):
        """Create user account for student access"""
        from accounts.models import User
        import secrets
        
        # Create user
        user = User.objects.create(
            username=self.code,
            user_type='student',
            student_code=self.code,
            access_token=secrets.token_urlsafe(32),
            language='ar',  # Default to Arabic
            is_active=True
        )
        
        self.user = user
    
    def calculate_discount_price(self, base_price=None):
        """Calculate price after applying discounts"""
        if not base_price:
            base_price = self.monthly_price if self.subscription_type == 'monthly' else self.per_session_price
        
        # Apply student discount first
        if self.student_discount > 0:
            base_price = base_price * (1 - self.student_discount / 100)
        
        # Apply group discount if student is in a group
        student_groups = self.student_groups.filter(is_active=True)
        for student_group in student_groups:
            group = student_group.group
            if group.group_discount > 0:
                # Only apply if student discount is lower or doesn't exist
                group_discount_amount = base_price * (group.group_discount / 100)
                student_discount_amount = base_price * (self.student_discount / 100)
                
                if group_discount_amount > student_discount_amount:
                    base_price = base_price * (1 - group.group_discount / 100)
                    break
        
        return base_price
    
    def update_remaining_amount(self):
        """Update remaining amount based on subscription type"""
        if self.subscription_type == 'free':
            self.remaining_amount = 0
        elif self.subscription_type == 'monthly':
            # Calculate monthly remaining based on groups
            total_monthly = Decimal('0')
            for student_group in self.student_groups.filter(is_active=True):
                # Use group price if available, otherwise fallback to student's base price
                price_to_use = student_group.group.monthly_price if student_group.group.monthly_price > 0 else self.monthly_price
                monthly_price = self.calculate_discount_price(price_to_use)
                total_monthly += monthly_price
            
            total_paid_monthly = self.get_monthly_payments_total()
            self.remaining_amount = total_monthly - total_paid_monthly
        
        self.save(update_fields=['remaining_amount'])
    
    def get_monthly_payments_total(self):
        """Get total monthly payments for current month"""
        from payments.models import Payment
        from django.utils import timezone
        
        current_month = timezone.now().date().replace(day=1)
        return Payment.objects.filter(
            student=self,
            payment_type='monthly',
            status='paid',
            payment_date__gte=current_month
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
    
    def update_remaining_sessions(self):
        """Update remaining sessions based on attendance"""
        if self.subscription_type == 'per_session':
            from attendance.models import Attendance
            attended_sessions = Attendance.objects.filter(
                student=self,
                status__in=['present', 'late']
            ).count()
            
            self.remaining_sessions = max(0, self.total_sessions_bought - attended_sessions)
            self.save(update_fields=['remaining_sessions'])
    
    def can_attend_session(self):
        """Check if student can attend a session"""
        if self.subscription_type == 'free':
            return True
        elif self.subscription_type == 'per_session':
            return self.remaining_sessions > 0
        elif self.subscription_type == 'monthly':
            return self.subscription_status == 'active'
        return False
    
    def get_attendance_rate(self, start_date=None, end_date=None):
        """Calculate attendance rate for given period"""
        from attendance.models import Attendance
        
        attendance_qs = Attendance.objects.filter(student=self)
        
        if start_date:
            attendance_qs = attendance_qs.filter(session__date__gte=start_date)
        if end_date:
            attendance_qs = attendance_qs.filter(session__date__lte=end_date)
        
        total = attendance_qs.count()
        if total == 0:
            return 0
        
        present = attendance_qs.filter(status__in=['present', 'late']).count()
        return round((present / total) * 100, 2)


class Parent(models.Model):
    """
    Parent model for linking to students
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='parents'
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='parent_profile'
    )
    
    # Basic Information
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    relationship = models.CharField(max_length=50, blank=True, null=True)  # Father, Mother, Guardian, etc.
    
    # System Fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'parents'
        indexes = [
            models.Index(fields=['teacher', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.relationship})"
    
    def save(self, *args, **kwargs):
        # Create user account if not exists
        if not self.user and self.teacher:
            self.create_user_account()
        
        super().save(*args, **kwargs)
    
    def create_user_account(self):
        """Create user account for parent access"""
        from accounts.models import User
        import secrets
        
        # Generate unique username
        username = f"parent_{self.id.hex[:8]}"
        
        # Create user
        user = User.objects.create(
            username=username,
            user_type='parent',
            access_token=secrets.token_urlsafe(32),
            language='ar',  # Default to Arabic
            is_active=True
        )
        
        self.user = user


class StudentParentLink(models.Model):
    """
    Many-to-many relationship between students and parents
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='parent_links')
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name='student_links')
    
    # Link Information
    is_primary_contact = models.BooleanField(default=False)
    can_receive_notifications = models.BooleanField(default=True)
    can_view_grades = models.BooleanField(default=True)
    can_view_attendance = models.BooleanField(default=True)
    can_view_payments = models.BooleanField(default=True)
    
    # System Fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'student_parent_links'
        unique_together = ['student', 'parent']
        indexes = [
            models.Index(fields=['student', 'is_active']),
            models.Index(fields=['parent', 'is_active']),
            models.Index(fields=['is_primary_contact']),
        ]
    
    def __str__(self):
        return f"{self.student.name} -> {self.parent.name}"


class StudentGroup(models.Model):
    """
    Many-to-many relationship between students and groups
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='student_groups')
    group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, related_name='group_students')
    
    # Enrollment Information
    enrollment_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Custom Pricing (overrides group pricing)
    custom_monthly_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    custom_session_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'student_groups'
        unique_together = ['student', 'group']
        indexes = [
            models.Index(fields=['student', 'is_active']),
            models.Index(fields=['group', 'is_active']),
            models.Index(fields=['enrollment_date']),
        ]
    
    def __str__(self):
        return f"{self.student.name} in {self.group.name}"
    
    def get_effective_monthly_price(self):
        """Get effective monthly price considering custom pricing"""
        if self.custom_monthly_price is not None:
            return self.custom_monthly_price
        return self.group.monthly_price or self.student.monthly_price
    
    def get_effective_session_price(self):
        """Get effective session price considering custom pricing"""
        if self.custom_session_price is not None:
            return self.custom_session_price
        return self.group.session_price or self.student.per_session_price