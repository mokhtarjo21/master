"""
Session Notification Tasks
Celery tasks for scheduling session reminders and notifications
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from notifications.models import Notification


@shared_task
def send_session_reminders():
    """
    Send reminders for upcoming sessions
    Run this task every 30 minutes
    """
    from teaching_sessions.models import Session
    from students.models import StudentGroup
    
    # Get reminder settings from teacher settings
    # Default: 1 hour before session
    reminder_minutes = 60
    
    # Calculate time window
    now = timezone.now()
    start_time = now + timedelta(minutes=reminder_minutes - 15)
    end_time = now + timedelta(minutes=reminder_minutes + 15)
    
    # Get upcoming sessions in the window
    upcoming_sessions = Session.objects.filter(
        start_time__gte=start_time,
        start_time__lte=end_time,
        status='scheduled'
    ).select_related('group', 'group__teacher')
    
    notifications_created = 0
    
    for session in upcoming_sessions:
        # Check if reminder already sent
        existing = Notification.objects.filter(
            notification_type='session_reminder',
            related_object_id=str(session.id),
            is_sent=True
        ).exists()
        
        if existing:
            continue
        
        # Get all students in the group
        students = StudentGroup.objects.filter(
            group=session.group,
            is_active=True
        ).select_related('student', 'student__user')
        
        for student_group in students:
            student = student_group.student
            
            # Create notification for student
            notification, created = Notification.objects.get_or_create(
                recipient=student.user,
                notification_type='session_reminder',
                related_object_id=str(session.id),
                defaults={
                    'title': f'تذكير بحصة {session.group.name}',
                    'message': f'لديك حصة {session.title or session.group.name} في {session.start_time.strftime("%I:%M %p")}',
                    'priority': 'high',
                    'category': 'sessions',
                    'action_url': f'/sessions/{session.id}/',
                    'metadata': {
                        'session_id': str(session.id),
                        'group_id': str(session.group.id),
                        'session_time': session.start_time.isoformat()
                    }
                }
            )
            
            if created:
                notifications_created += 1
        
        # Also notify teacher
        if session.group.teacher:
            Notification.objects.get_or_create(
                recipient=session.group.teacher,
                notification_type='session_reminder',
                related_object_id=str(session.id),
                defaults={
                    'title': f'تذكير بحصة {session.group.name}',
                    'message': f'لديك حصة {session.title or session.group.name} في {session.start_time.strftime("%I:%M %p")}',
                    'priority': 'high',
                    'category': 'sessions'
                }
            )
            notifications_created += 1
    
    return {
        'sessions_checked': upcoming_sessions.count(),
        'notifications_created': notifications_created
    }


@shared_task
def mark_completed_sessions():
    """
    Mark sessions as completed after their end time
    Run this task every hour
    """
    from teaching_sessions.models import Session
    
    now = timezone.now()
    
    # Get sessions that ended but still scheduled
    past_sessions = Session.objects.filter(
        end_time__lt=now,
        status='scheduled'
    )
    
    updated_count = past_sessions.update(status='completed')
    
    return {
        'sessions_updated': updated_count
    }


@shared_task
def send_daily_session_summary():
    """
    Send daily summary of sessions to teachers
    Run this task every day at 8:00 AM
    """
    from teaching_sessions.models import Session
    from accounts.models import User
    
    today = timezone.now().date()
    
    teachers = User.objects.filter(user_type='teacher', is_active=True)
    
    notifications_sent = 0
    
    for teacher in teachers:
        # Get today's sessions
        today_sessions = Session.objects.filter(
            group__teacher=teacher,
            start_time__date=today
        ).select_related('group').order_by('start_time')
        
        if not today_sessions.exists():
            continue
        
        # Create summary message
        session_list = '\n'.join([
            f"- {s.group.name} في {s.start_time.strftime('%I:%M %p')}"
            for s in today_sessions
        ])
        
        Notification.objects.create(
            recipient=teacher,
            notification_type='daily_summary',
            title=f'ملخص حصص اليوم ({today_sessions.count()} حصة)',
            message=f'لديك {today_sessions.count()} حصة اليوم:\n{session_list}',
            priority='normal',
            category='sessions'
        )
        notifications_sent += 1
    
    return {
        'teachers_notified': notifications_sent
    }


@shared_task
def send_absence_alerts():
    """
    Send alerts for students who are absent
    Run this task 30 minutes after session start time
    """
    from teaching_sessions.models import Session
    from attendance.models import Attendance
    from students.models import StudentGroup
    
    # Get sessions that started 30 minutes ago
    check_time = timezone.now() - timedelta(minutes=30)
    
    sessions = Session.objects.filter(
        start_time__lte=check_time,
        start_time__gte=check_time - timedelta(minutes=15),
        status='in_progress'
    ).select_related('group')
    
    alerts_sent = 0
    
    for session in sessions:
        # Get all students in group
        students = StudentGroup.objects.filter(
            group=session.group,
            is_active=True
        ).select_related('student', 'student__user')
        
        for student_group in students:
            student = student_group.student
            
            # Check if student has attendance record
            has_attendance = Attendance.objects.filter(
                session=session,
                student=student
            ).exists()
            
            if not has_attendance:
                # Send absence alert to parent
                if student.parent and student.parent.user:
                    Notification.objects.create(
                        recipient=student.parent.user,
                        notification_type='absence_alert',
                        title=f'تنبيه: غياب {student.name}',
                        message=f'{student.name} غائب عن حصة {session.group.name}',
                        priority='high',
                        category='attendance',
                        related_object_id=str(session.id),
                        metadata={
                            'student_id': str(student.id),
                            'session_id': str(session.id)
                        }
                    )
                    alerts_sent += 1
    
    return {
        'sessions_checked': sessions.count(),
        'absence_alerts_sent': alerts_sent
    }
