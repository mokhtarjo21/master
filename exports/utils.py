"""
Export Generation Utilities
CSV, Excel, and PDF generators for different data types
"""
import csv
from io import StringIO, BytesIO
from django.utils import timezone


def generate_students_csv(students, fields=None):
    """
    Generate CSV export for students
    """
    output = StringIO()
    
    # Default fields if not specified
    default_fields = [
        'name', 'student_code', 'phone', 'email',
        'subscription_type', 'monthly_price', 'created_at'
    ]
    fields = fields or default_fields
    
    # Create CSV writer
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(fields)
    
    # Write data rows
    for student in students:
        row = []
        for field in fields:
            value = getattr(student, field, '')
            # Handle special cases
            if value is None:
                value = ''
            elif hasattr(value, 'strftime'):  # DateTime
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            row.append(str(value))
        writer.writerow(row)
    
    # Return encoded content
    return output.getvalue().encode('utf-8-sig')  # BOM for Excel compatibility


def generate_payments_csv(payments, fields=None):
    """
    Generate CSV export for payments
    """
    output = StringIO()
    
    # Default fields
    default_fields = [
        'student__name', 'student__student_code', 'amount', 
        'amount_paid', 'remaining_amount', 'status',
        'payment_method', 'due_date', 'created_at'
    ]
    fields = fields or default_fields
    
    writer = csv.writer(output)
    
    # Write header (clean field names)
    headers = [field.replace('__', '_').replace('_', ' ').title() for field in fields]
    writer.writerow(headers)
    
    # Write data using values() for related fields
    for payment in payments.values(*fields):
        row = []
        for field in fields:
            value = payment.get(field, '')
            if value is None:
                value = ''
            elif isinstance(value, (timezone.datetime, timezone.date)):
                value = value.strftime('%Y-%m-%d')
            row.append(str(value))
        writer.writerow(row)
    
    return output.getvalue().encode('utf-8-sig')


def generate_attendance_csv(attendance_records, fields=None):
    """
    Generate CSV export for attendance
    """
    output = StringIO()
    
    default_fields = [
        'student__name', 'student__student_code',
        'session__group__name', 'date', 'status', 'notes'
    ]
    fields = fields or default_fields
    
    writer = csv.writer(output)
    
    # Headers
    headers = [field.replace('__', '_').replace('_', ' ').title() for field in fields]
    writer.writerow(headers)
    
    # Data
    for record in attendance_records.values(*fields):
        row = []
        for field in fields:
            value = record.get(field, '')
            if value is None:
                value = ''
            elif isinstance(value, (timezone.datetime, timezone.date)):
                value = value.strftime('%Y-%m-%d')
            row.append(str(value))
        writer.writerow(row)
    
    return output.getvalue().encode('utf-8-sig')


def generate_grades_csv(grades, fields=None):
    """
    Generate CSV export for grades
    """
    output = StringIO()
    
    default_fields = [
        'student__name', 'student__student_code',
        'subject', 'grade_value', 'max_grade',
        'grade_date', 'notes'
    ]
    fields = fields or default_fields
    
    writer = csv.writer(output)
    
    # Headers
    headers = [field.replace('__', '_').replace('_', ' ').title() for field in fields]
    writer.writerow(headers)
    
    # Data
    for grade in grades.values(*fields):
        row = []
        for field in fields:
            value = grade.get(field, '')
            if value is None:
                value = ''
            elif isinstance(value, (timezone.datetime, timezone.date)):
                value = value.strftime('%Y-%m-%d')
            row.append(str(value))
        writer.writerow(row)
    
    return output.getvalue().encode('utf-8-sig')


def generate_groups_csv(groups, fields=None):
    """
    Generate CSV export for groups
    """
    output = StringIO()
    
    default_fields = [
        'name', 'subject', 'grade_level', 'max_students',
        'schedule', 'is_active', 'created_at'
    ]
    fields = fields or default_fields
    
    writer = csv.writer(output)
    
    # Headers
    writer.writerow(fields)
    
    # Data
    for group in groups:
        row = []
        for field in fields:
            value = getattr(group, field, '')
            if value is None:
                value = ''
            elif hasattr(value, 'strftime'):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value, bool):
                value = 'Yes' if value else 'No'
            row.append(str(value))
        writer.writerow(row)
    
    return output.getvalue().encode('utf-8-sig')


def save_export_file(export, content, filename):
    """
    Helper to save export file and update export object
    """
    from django.core.files.base import ContentFile
    
    export.file.save(filename, ContentFile(content), save=False)
    export.status = 'completed'
    export.file_size = len(content)
    export.generated_at = timezone.now()
    export.save()
    
    return export
