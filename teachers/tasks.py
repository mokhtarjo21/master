"""
Teacher Background Tasks
"""
from celery import shared_task
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from .models import TeacherStats
from accounts.models import User


@shared_task
def generate_daily_teacher_stats():
    """Generate daily statistics for all teachers"""
    today = timezone.now().date()
    teachers = User.objects.filter(user_type='teacher', is_active=True)
    
    for teacher in teachers:
        # Check if stats already exist
        if TeacherStats.objects.filter(
            teacher=teacher,
            date=today,
            stat_type='daily'
        ).exists():
            continue
        
        # Calculate daily statistics
        stats_data = calculate_teacher_stats(teacher, today, 'daily')
        
        TeacherStats.objects.create(
            teacher=teacher,
            date=today,
            stat_type='daily',
            **stats_data
        )


@shared_task
def generate_monthly_teacher_stats():
    """Generate monthly statistics for all teachers"""
    today = timezone.now().date()
    month_start = today.replace(day=1)
    teachers = User.objects.filter(user_type='teacher', is_active=True)
    
    for teacher in teachers:
        # Check if stats already exist
        if TeacherStats.objects.filter(
            teacher=teacher,
            date=month_start,
            stat_type='monthly'
        ).exists():
            continue
        
        # Calculate monthly statistics
        stats_data = calculate_teacher_stats(teacher, month_start, 'monthly')
        
        TeacherStats.objects.create(
            teacher=teacher,
            date=month_start,
            stat_type='monthly',
            **stats_data
        )


def calculate_teacher_stats(teacher, date_obj, stat_type):
    """Calculate statistics for a teacher for given date and type"""
    from students.models import Student
    from groups.models import Group
    from teaching_sessions.models import Session
    from attendance.models import Attendance
    from payments.models import Payment
    
    if stat_type == 'daily':
        date_filter = {'created_at__date': date_obj}
        session_filter = {'date': date_obj}
    else:  # monthly
        date_filter = {
            'created_at__year': date_obj.year,
            'created_at__month': date_obj.month
        }
        session_filter = {
            'date__year': date_obj.year,
            'date__month': date_obj.month
        }
    
    # Student statistics
    students = Student.objects.filter(teacher=teacher, is_active=True)
    total_students = students.count()
    active_students = students.filter(subscription_status='active').count()
    new_students = Student.objects.filter(teacher=teacher, **date_filter).count()
    
    # Group statistics
    groups = Group.objects.filter(teacher=teacher, is_active=True)
    total_groups = groups.count()
    active_groups = groups.count()  # All groups are considered active if is_active=True
    
    # Session statistics
    sessions = Session.objects.filter(group__teacher=teacher, **session_filter)
    total_sessions = sessions.count()
    completed_sessions = sessions.filter(status='completed').count()
    cancelled_sessions = sessions.filter(status='cancelled').count()
    
    # Financial statistics
    payments = Payment.objects.filter(student__teacher=teacher)
    if stat_type == 'daily':
        payments = payments.filter(created_at__date=date_obj)
    else:
        payments = payments.filter(
            created_at__year=date_obj.year,
            created_at__month=date_obj.month
        )
    
    total_revenue = payments.filter(status='paid').aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0')
    
    pending_payments = Payment.objects.filter(
        student__teacher=teacher,
        status='pending'
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
    
    overdue_payments = Payment.objects.filter(
        student__teacher=teacher,
        status='overdue'
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
    
    # Attendance statistics
    attendance_qs = Attendance.objects.filter(
        session__group__teacher=teacher,
        **{'session__' + k: v for k, v in session_filter.items()}
    )
    
    total_attendance = attendance_qs.count()
    present_count = attendance_qs.filter(status='present').count()
    absent_count = attendance_qs.filter(status='absent').count()
    late_count = attendance_qs.filter(status='late').count()
    
    return {
        'total_students': total_students,
        'active_students': active_students,
        'new_students': new_students,
        'total_groups': total_groups,
        'active_groups': active_groups,
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'cancelled_sessions': cancelled_sessions,
        'total_revenue': total_revenue,
        'pending_payments': pending_payments,
        'overdue_payments': overdue_payments,
        'total_attendance': total_attendance,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
    }