"""
Payment Models
Comprehensive payment management with multiple methods and financial logic
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid


class Payment(models.Model):
    """
    Core Payment model
    """
    PAYMENT_TYPES = [
        ('monthly', 'Monthly Subscription'),
        ('session', 'Per Session'),
        ('registration', 'Registration Fee'),
        ('material', 'Materials'),
        ('other', 'Other'),
    ]
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('mobile_payment', 'Mobile Payment'),
        ('check', 'Check'),
        ('online', 'Online Payment'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='payments')
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        help_text='المجموعة المرتبطة بهذه الدفعة'
    )
    
    # Payment Details
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='monthly')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Session Details
    session_count = models.PositiveIntegerField(default=0, help_text="Number of sessions this payment purchases")
    
    # Payment Information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Dates
    due_date = models.DateField()
    payment_date = models.DateField(blank=True, null=True)
    
    # Period (for monthly payments)
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)
    
    # Reference Information
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Discounts
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_reason = models.CharField(max_length=200, blank=True, null=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)
    
    # System Fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_payments'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['group', 'status']),
            models.Index(fields=['student', 'group']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['payment_type', 'status']),
            models.Index(fields=['period_start', 'period_end']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.name} - {self.amount} - {self.status}"
    
    def save(self, *args, **kwargs):
        # Calculate remaining amount
        self.remaining_amount = self.amount - self.amount_paid
        
        # Track if this is transitioning to paid
        was_paid = False
        if self.pk:
            old_payment = Payment.objects.filter(pk=self.pk).first()
            if old_payment and old_payment.status == 'paid':
                was_paid = True
        
        # Update status based on payment
        if self.amount_paid == 0:
            if self.due_date < timezone.now().date():
                self.status = 'overdue'
            else:
                self.status = 'pending'
        elif self.amount_paid >= self.amount:
            self.status = 'paid'
            self.payment_date = self.payment_date or timezone.now().date()
        else:
            self.status = 'partial'
        
        # Generate reference number if not provided
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        
        super().save(*args, **kwargs)
        
        # If it just became paid, and pays for sessions, add those to the student
        if self.status == 'paid' and not was_paid and self.session_count > 0:
            self.student.remaining_sessions += self.session_count
            self.student.total_sessions_bought += self.session_count
            
            # Auto-switch the student to per-session if they just paid for sessions
            if self.student.subscription_type != 'per_session':
                self.student.subscription_type = 'per_session'
            
            self.student.save(update_fields=['remaining_sessions', 'total_sessions_bought', 'subscription_type'])
        
        # Update student financial totals
        self.student.update_remaining_amount()
    
    def generate_reference_number(self):
        """Generate unique reference number"""
        import random
        import string
        
        prefix = 'PAY'
        timestamp = timezone.now().strftime('%Y%m%d')
        random_suffix = ''.join(random.choices(string.digits, k=4))
        
        return f"{prefix}-{timestamp}-{random_suffix}"
    
    def add_payment(self, amount, payment_method='cash', notes=''):
        """Add a payment amount"""
        if amount <= 0:
            raise ValueError("Payment amount must be positive")
        
        if self.amount_paid + amount > self.amount:
            raise ValueError("Payment amount exceeds remaining balance")
        
        self.amount_paid += Decimal(str(amount))
        self.payment_method = payment_method
        
        if notes:
            if self.notes:
                self.notes += f"\n{notes}"
            else:
                self.notes = notes
        
        self.save()
        
        # Create payment transaction record
        PaymentTransaction.objects.create(
            payment=self,
            amount=amount,
            payment_method=payment_method,
            notes=notes,
            transaction_date=timezone.now().date()
        )
    
    def is_overdue(self):
        """Check if payment is overdue"""
        return self.due_date < timezone.now().date() and self.status in ['pending', 'partial']
    
    def days_overdue(self):
        """Calculate days overdue"""
        if self.is_overdue():
            return (timezone.now().date() - self.due_date).days
        return 0
    
    def apply_discount(self, discount_amount, reason=''):
        """Apply discount to payment"""
        if discount_amount < 0 or discount_amount > self.amount:
            raise ValueError("Invalid discount amount")
        
        self.discount_amount = Decimal(str(discount_amount))
        self.discount_reason = reason
        self.amount = self.amount - self.discount_amount
        self.save()


class PaymentTransaction(models.Model):
    """
    Individual payment transactions for tracking partial payments
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='transactions')
    
    # Transaction Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=Payment.PAYMENT_METHODS)
    transaction_date = models.DateField()
    
    # Reference Information
    transaction_reference = models.CharField(max_length=100, blank=True, null=True)
    receipt_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # System Fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payment_transactions'
        indexes = [
            models.Index(fields=['payment', 'transaction_date']),
            models.Index(fields=['transaction_date']),
        ]
        ordering = ['-transaction_date']
    
    def __str__(self):
        return f"{self.payment.student.name} - {self.amount} - {self.transaction_date}"


class PaymentPlan(models.Model):
    """
    Payment plans for installments
    """
    PLAN_STATUS = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('defaulted', 'Defaulted'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='payment_plans')
    
    # Plan Details
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    installment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    number_of_installments = models.PositiveIntegerField()
    
    # Schedule
    start_date = models.DateField()
    installment_frequency = models.CharField(max_length=20, choices=[
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
    ], default='monthly')
    
    # Status
    status = models.CharField(max_length=20, choices=PLAN_STATUS, default='active')
    
    # Progress
    installments_paid = models.PositiveIntegerField(default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Notes
    description = models.TextField(blank=True, null=True)
    
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
        db_table = 'payment_plans'
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['start_date']),
        ]
    
    def __str__(self):
        return f"{self.student.name} - Payment Plan - {self.total_amount}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Create installment payments if this is a new plan
        if not hasattr(self, '_installments_created'):
            self.create_installment_payments()
            self._installments_created = True
    
    def create_installment_payments(self):
        """Create individual payment records for each installment"""
        from datetime import timedelta
        
        current_date = self.start_date
        
        for i in range(self.number_of_installments):
            # Calculate due date
            if self.installment_frequency == 'weekly':
                due_date = current_date + timedelta(weeks=i)
            elif self.installment_frequency == 'biweekly':
                due_date = current_date + timedelta(weeks=i*2)
            else:  # monthly
                # Add months (approximate)
                month = current_date.month + i
                year = current_date.year + (month - 1) // 12
                month = ((month - 1) % 12) + 1
                due_date = current_date.replace(year=year, month=month)
            
            Payment.objects.create(
                student=self.student,
                payment_type='monthly',
                amount=self.installment_amount,
                due_date=due_date,
                notes=f"Installment {i+1} of {self.number_of_installments}",
                created_by=self.created_by
            )
    
    def update_progress(self):
        """Update payment plan progress"""
        plan_payments = Payment.objects.filter(
            student=self.student,
            notes__contains=f"of {self.number_of_installments}",
            status='paid'
        )
        
        self.installments_paid = plan_payments.count()
        self.amount_paid = plan_payments.aggregate(
            total=models.Sum('amount_paid')
        )['total'] or Decimal('0')
        
        # Update status
        if self.installments_paid >= self.number_of_installments:
            self.status = 'completed'
        elif self.amount_paid > 0:
            self.status = 'active'
        
        self.save(update_fields=['installments_paid', 'amount_paid', 'status'])


class PaymentReminder(models.Model):
    """
    Payment reminders and notifications
    """
    REMINDER_TYPES = [
        ('due_soon', 'Due Soon'),
        ('overdue', 'Overdue'),
        ('final_notice', 'Final Notice'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='reminders')
    
    # Reminder Details
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    reminder_date = models.DateField()
    
    # Message
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Status
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(blank=True, null=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payment_reminders'
        indexes = [
            models.Index(fields=['payment', 'reminder_type']),
            models.Index(fields=['reminder_date', 'is_sent']),
        ]
    
    def __str__(self):
        return f"{self.payment.student.name} - {self.reminder_type}"


class PaymentMethod(models.Model):
    """
    Available payment methods configuration
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    
    # Method Details
    name = models.CharField(max_length=100)
    method_type = models.CharField(max_length=20, choices=Payment.PAYMENT_METHODS)
    
    # Configuration
    account_details = models.JSONField(default=dict)  # Store account numbers, etc.
    instructions = models.TextField(blank=True, null=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_methods'
        indexes = [
            models.Index(fields=['teacher', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.teacher.username} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default method per teacher
        if self.is_default:
            PaymentMethod.objects.filter(
                teacher=self.teacher,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        
        super().save(*args, **kwargs)