"""
Payment Utilities
Helper functions for payment calculations
"""
from decimal import Decimal
from datetime import date
from django.utils import timezone
from .models import Payment


def calculate_monthly_payment(student, group, month=None, year=None):
    """
    Calculate monthly payment amount with all discounts applied
    
    Priority:
    1. Free student = 0
    2. Student discount (fixed amount) first
    3. Group discount (fixed amount) second
    
    Args:
        student: Student instance
        group: Group instance
        month: Optional month (defaults to current)
        year: Optional year (defaults to current)
    
    Returns:
        Decimal: Final amount due
    """
    # Free student pays nothing
    if student.subscription_type == 'free':
        return Decimal('0')
    
    # Base price from group
    base_price = group.monthly_price
    
    # Apply student discount first (priority 1)
    # Note: Currently student_discount is percentage, need to convert or add new field
    if hasattr(student, 'student_discount_amount') and student.student_discount_amount > 0:
        base_price -= student.student_discount_amount
    elif student.student_discount > 0:
        # If it's percentage, calculate amount
        discount_amount = base_price * (student.student_discount / Decimal('100'))
        base_price -= discount_amount
    
    # Apply group discount second (priority 2) - only if student discount wasn't applied
    elif hasattr(group, 'group_discount_amount') and group.group_discount_amount > 0:
        base_price -= group.group_discount_amount
    elif group.group_discount > 0:
        # If it's percentage, calculate amount
        discount_amount = base_price * (group.group_discount / Decimal('100'))
        base_price -= discount_amount
    
    # Ensure non-negative
    return max(base_price, Decimal('0'))


def get_or_create_monthly_payment(student, group, month=None, year=None):
    """
    Get or create payment for student in group for specific month
    
    Args:
        student: Student instance
        group: Group instance
        month: Optional month (defaults to current)
        year: Optional year (defaults to current)
    
    Returns:
        tuple: (Payment instance, created boolean)
    """
    if month is None or year is None:
        today = timezone.now().date()
        month = month or today.month
        year = year or today.year
    
    # Calculate period dates
    period_start = date(year, month, 1)
    
    # Last day of month
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    period_end = date(year, month, last_day)
    
    # Calculate amount
    amount = calculate_monthly_payment(student, group, month, year)
    
    # Get or create payment
    payment, created = Payment.objects.get_or_create(
        student=student,
        group=group,
        period_start=period_start,
        period_end=period_end,
        defaults={
            'amount': amount,
            'payment_type': 'monthly',
            'due_date': period_start,
            'status': 'pending' if amount > 0 else 'paid',
            'remaining_amount': amount
        }
    )
    
    # If not created but amount changed, update it
    if not created and payment.amount != amount:
        payment.amount = amount
        payment.remaining_amount = amount - payment.amount_paid
        payment.save()
    
    return payment, created


def sync_monthly_payments_for_teacher(teacher, month=None, year=None):
    """
    Auto-generate/update all monthly payments for teacher's students
    
    Args:
        teacher: User instance (teacher)
        month: Optional month (defaults to current)
        year: Optional year (defaults to current)
    
    Returns:
        dict: Statistics about created/updated payments
    """
    from students.models import StudentGroup
    
    if month is None or year is None:
        today = timezone.now().date()
        month = month or today.month
        year = year or today.year
    
    stats = {
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': []
    }
    
    # Get all active student-group enrollments
    enrollments = StudentGroup.objects.filter(
        student__teacher=teacher,
        is_active=True,
        student__is_active=True,
        group__is_active=True,
        student__subscription_type='monthly'  # Only monthly subscriptions
    ).select_related('student', 'group')
    
    for enrollment in enrollments:
        try:
            payment, created = get_or_create_monthly_payment(
                student=enrollment.student,
                group=enrollment.group,
                month=month,
                year=year
            )
            
            if created:
                stats['created'] += 1
            else:
                stats['updated'] += 1
                
        except Exception as e:
            stats['errors'].append({
                'student': enrollment.student.name,
                'group': enrollment.group.name,
                'error': str(e)
            })
            stats['skipped'] += 1
    
    return stats


def calculate_student_overdue(student):
    """
    Calculate total overdue amount for a student
    
    Args:
        student: Student instance
    
    Returns:
        dict: Overdue details
    """
    from django.db.models import Sum
    
    today = timezone.now().date()
    
    overdue_payments = Payment.objects.filter(
        student=student,
        due_date__lt=today,
        status__in=['pending', 'partial'],
        is_active=True
    )
    
    total_overdue = overdue_payments.aggregate(
        total=Sum('remaining_amount')
    )['total'] or Decimal('0')
    
    return {
        'total_overdue': total_overdue,
        'count': overdue_payments.count(),
        'payments': overdue_payments
    }
