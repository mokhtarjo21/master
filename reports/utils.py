"""
Report Generation Utilities
Simple generators for different report types
"""
from django.utils import timezone
from io import BytesIO
import json
import csv


def generate_student_report_json(student, period_start=None, period_end=None):
    """Generate student report as JSON"""
    from grades.models import Grade
    from attendance.models import Attendance
    from payments.models import Payment
    
    # Filters
    filters = {}
    if period_start:
        filters['created_at__gte'] = period_start
    if period_end:
        filters['created_at__lte'] = period_end
    
    # Collect data
    data = {
        'student': {
            'id': str(student.id),
            'name': student.name,
            'code': student.student_code,
            'phone': student.phone,
            'subscription_type': student.subscription_type,
        },
        'period': {
            'start': str(period_start) if period_start else None,
            'end': str(period_end) if period_end else None,
        },
        'grades': list(Grade.objects.filter(
            student=student, **filters
        ).values('subject', 'grade_value', 'max_grade', 'grade_date')),
        'attendance': list(Attendance.objects.filter(
            student=student, **filters
        ).values('date', 'status', 'notes')),
        'payments': list(Payment.objects.filter(
            student=student, **filters
        ).values('amount', 'amount_paid', 'payment_date', 'status')),
    }
    
    # Calculate statistics
    total_grades = len(data['grades'])
    attendance_records = data['attendance']
    present_count = len([a for a in attendance_records if a['status'] == 'present'])
    total_attendance = len(attendance_records)
    
    data['statistics'] = {
        'total_grades': total_grades,
        'attendance_rate': (present_count / total_attendance * 100) if total_attendance > 0 else 0,
        'total_payments': len(data['payments']),
        'total_paid': sum(p['amount_paid'] or 0 for p in data['payments']),
    }
    
    return json.dumps(data, indent=2, default=str)


def generate_financial_report_json(teacher, period_start, period_end):
    """Generate financial report as JSON"""
    from payments.models import Payment
    from django.db.models import Sum, Count, Q
    
    payments = Payment.objects.filter(
        student__teacher=teacher,
        created_at__date__gte=period_start,
        created_at__date__lte=period_end
    )
    
    data = {
        'period': {
            'start': str(period_start),
            'end': str(period_end),
        },
        'summary': {
            'total_revenue': float(payments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0),
            'total_expected': float(payments.aggregate(Sum('amount'))['amount__sum'] or 0),
            'total_pending': float(payments.aggregate(Sum('remaining_amount'))['remaining_amount__sum'] or 0),
            'total_payments': payments.count(),
            'paid_payments': payments.filter(status='paid').count(),
            'pending_payments': payments.filter(status='pending').count(),
        },
        'by_payment_method': {},
        'by_student': []
    }
    
    # By payment method
    for method in ['cash', 'bank', 'online']:
        method_payments = payments.filter(payment_method=method)
        data['by_payment_method'][method] = {
            'count': method_payments.count(),
            'total': float(method_payments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0)
        }
    
    # Top students by payments
    from students.models import Student
    students = Student.objects.filter(teacher=teacher)
    for student in students[:10]:
        student_payments = payments.filter(student=student)
        if student_payments.exists():
            data['by_student'].append({
                'student_name': student.name,
                'total_paid': float(student_payments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0),
                'payment_count': student_payments.count()
            })
    
    return json.dumps(data, indent=2, default=str)


def generate_attendance_report_json(teacher, period_start, period_end, group_id=None):
    """Generate attendance report as JSON"""
    from attendance.models import Attendance
    from students.models import Student
    from django.db.models import Count, Q
    
    filters = {
        'session__group__teacher': teacher,
        'date__gte': period_start,
        'date__lte': period_end,
    }
    
    if group_id:
        filters['session__group_id'] = group_id
    
    attendances = Attendance.objects.filter(**filters)
    
    data = {
        'period': {
            'start': str(period_start),
            'end': str(period_end),
        },
        'summary': {
            'total_records': attendances.count(),
            'present': attendances.filter(status='present').count(),
            'absent': attendances.filter(status='absent').count(),
            'late': attendances.filter(status='late').count(),
            'excused': attendances.filter(status='excused').count(),
        },
        'by_student': []
    }
    
    # Calculate attendance rate
    total = data['summary']['total_records']
    if total > 0:
        data['summary']['attendance_rate'] = round(
            (data['summary']['present'] + data['summary']['late']) / total * 100, 2
        )
    else:
        data['summary']['attendance_rate'] = 0
    
    # By student
    students = Student.objects.filter(teacher=teacher)
    for student in students:
        student_attendance = attendances.filter(student=student)
        if student_attendance.exists():
            total_student = student_attendance.count()
            present_student = student_attendance.filter(Q(status='present') | Q(status='late')).count()
            
            data['by_student'].append({
                'student_name': student.name,
                'total_sessions': total_student,
                'present': student_attendance.filter(status='present').count(),
                'absent': student_attendance.filter(status='absent').count(),
                'late': student_attendance.filter(status='late').count(),
                'attendance_rate': round(present_student / total_student * 100, 2) if total_student > 0 else 0
            })
    
    return json.dumps(data, indent=2, default=str)


def generate_grades_report_json(teacher, period_start, period_end, subject=None):
    """Generate grades report as JSON"""
    from grades.models import Grade
    from students.models import Student
    from django.db.models import Avg, Count
    
    filters = {
        'student__teacher': teacher,
        'grade_date__gte': period_start,
        'grade_date__lte': period_end,
    }
    
    if subject:
        filters['subject'] = subject
    
    grades = Grade.objects.filter(**filters)
    
    data = {
        'period': {
            'start': str(period_start),
            'end': str(period_end),
        },
        'summary': {
            'total_grades': grades.count(),
            'average_grade': float(grades.aggregate(Avg('grade_value'))['grade_value__avg'] or 0),
        },
        'by_subject': {},
        'by_student': []
    }
    
    # By subject
    subjects = grades.values_list('subject', flat=True).distinct()
    for subj in subjects:
        subject_grades = grades.filter(subject=subj)
        data['by_subject'][subj] = {
            'count': subject_grades.count(),
            'average': float(subject_grades.aggregate(Avg('grade_value'))['grade_value__avg'] or 0),
        }
    
    # By student
    students = Student.objects.filter(teacher=teacher)
    for student in students:
        student_grades = grades.filter(student=student)
        if student_grades.exists():
            data['by_student'].append({
                'student_name': student.name,
                'total_grades': student_grades.count(),
                'average_grade': float(student_grades.aggregate(Avg('grade_value'))['grade_value__avg'] or 0),
            })
    
    return json.dumps(data, indent=2, default=str)


def save_report_to_file(content, report, format_type='json'):
    """Save report content to file"""
    from django.core.files.base import ContentFile
    
    filename = f"report_{report.id}.{format_type}"
    
    if isinstance(content, str):
        content = content.encode('utf-8')
    
    report.file.save(filename, ContentFile(content), save=False)
    report.status = 'completed'
    report.generated_at = timezone.now()
    report.save()
    
    return report
