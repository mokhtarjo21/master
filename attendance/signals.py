"""
Attendance Signals
Automatic notifications for attendance events
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Attendance


@receiver(post_save, sender=Attendance)
def notify_on_attendance_event(sender, instance, created, **kwargs):
    """Send notification when student is absent or late"""
    if not created:
        return
    
    # Only notify on absence or late
    if instance.status not in ['absent', 'late']:
        return
    
    from notifications.models import Notification
    from students.models import StudentParentLink
    
    student = instance.student
    session = instance.session
    
    # Prepare notification message
    if instance.status == 'absent':
        title = f"غياب: {student.name}"
        message = f"الطالب {student.name} غائب عن حصة {session.group.name} بتاريخ {session.date}"
    else:  # late
        title = f"تأخير: {student.name}"
        message = f"الطالب {student.name} تأخر عن حصة {session.group.name} بتاريخ {session.date}"
        if instance.notes:
            message += f"\n\nملاحظات: {instance.notes}"
    
    # Send to parents
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
            title=title,
            message=message,
            notification_type='attendance',
            channel='whatsapp',
            metadata={
                'student_id': str(student.id),
                'student_name': student.name,
                'session_id': str(session.id),
                'group_id': str(session.group.id),
                'attendance_status': instance.status,
                'date': str(session.date)
            }
        )
