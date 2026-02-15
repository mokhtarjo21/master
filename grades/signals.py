"""
Grades Signals
Automatic notifications for grade events
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Grade


@receiver(post_save, sender=Grade)
def notify_on_new_grade(sender, instance, created, **kwargs):
    """Send notification when a new grade is added"""
    if not created:
        return
    
    from notifications.models import Notification
    from students.models import StudentParentLink
    
    student = instance.student
    
    # Prepare notification message
    title = f"درجة جديدة: {student.name}"
    message = f"تم إضافة درجة جديدة للطالب {student.name}\n"
    message += f"المادة/الموضوع: {instance.subject}\n"
    message += f"الدرجة: {instance.grade_value}"
    
    if instance.max_grade:
        message += f" من {instance.max_grade}"
        percentage = (instance.grade_value / instance.max_grade) * 100
        message += f" ({percentage:.1f}%)"
    
    if instance.notes:
        message += f"\n\nملاحظات: {instance.notes}"
    
    # Determine if grade is low (less than 60%)
    is_low_grade = False
    if instance.max_grade:
        percentage = (instance.grade_value / instance.max_grade) * 100
        is_low_grade = percentage < 60
    
    # Send to student
    if student.user:
        Notification.objects.create(
            teacher=student.teacher,
            recipient_type='student',
            recipient_id=student.id,
            recipient_name=student.name,
            recipient_phone=student.whatsapp_number or student.phone,
            recipient_email=student.email,
            title=title,
            message=message,
            notification_type='grade',
            channel='whatsapp',
            metadata={
                'grade_id': str(instance.id),
                'student_id': str(student.id),
                'subject': instance.subject,
                'grade_value': str(instance.grade_value),
                'max_grade': str(instance.max_grade) if instance.max_grade else None,
                'is_low_grade': is_low_grade,
                'session_id': str(instance.session.id) if instance.session else None
            }
        )
    
    # Send to parents (especially if grade is low)
    if is_low_grade:
        parent_title = f"⚠️ درجة منخفضة: {student.name}"
        parent_message = message + "\n\n⚠️ يرجى المتابعة مع الطالب"
    else:
        parent_title = title
        parent_message = message
    
    parent_links = StudentParentLink.objects.filter(
        student=student,
        is_active=True
    ).select_related('parent')
    
    for link in parent_links:
        parent = link.parent
        Notification.objects.create(
            teacher=student.teacher,
            recipient_type='parent',
            recipient_id=parent.id,
            recipient_name=parent.name,
            recipient_phone=parent.whatsapp_number or parent.phone,
            recipient_email=parent.email,
            title=parent_title,
            message=parent_message,
            notification_type='grade',
            channel='whatsapp',
            metadata={
                'grade_id': str(instance.id),
                'student_id': str(student.id),
                'student_name': student.name,
                'subject': instance.subject,
                'grade_value': str(instance.grade_value),
                'max_grade': str(instance.max_grade) if instance.max_grade else None,
                'is_low_grade': is_low_grade
            }
        )
