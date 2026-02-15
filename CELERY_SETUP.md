# Celery Beat Schedule Configuration

Add this to your `settings.py` file to enable automatic session notifications:

```python
# Celery Beat Schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Send session reminders every 30 minutes
    'send-session-reminders': {
        'task': 'teaching_sessions.tasks.send_session_reminders',
        'schedule': crontab(minute='*/30'),  # Run every 30 minutes
    },
    
    # Mark completed sessions every hour
    'mark-completed-sessions': {
        'task': 'teaching_sessions.tasks.mark_completed_sessions',
        'schedule': crontab(minute=0),  # Run at the start of every hour
    },
    
    # Send daily session summary at 8:00 AM
    'daily-session-summary': {
        'task': 'teaching_sessions.tasks.send_daily_session_summary',
        'schedule': crontab(hour=8, minute=0),  # Run at 8:00 AM
    },
    
    # Send absence alerts 30 minutes after sessions
    'send-absence-alerts': {
        'task': 'teaching_sessions.tasks.send_absence_alerts',
        'schedule': crontab(minute='*/15'),  # Check every 15 minutes
    },
}
```

## Usage

**Start Celery Worker:**
```bash
celery -A smart_teacher_assistant worker -l info
```

**Start Celery Beat:**
```bash
celery -A smart_teacher_assistant beat -l info
```

**Or both together:**
```bash
celery -A smart_teacher_assistant worker -B -l info
```

## What It Does

1. **Session Reminders** (Every 30 min)
   - Sends notification 1 hour before session
   - To students and teacher
   - High priority

2. **Auto-Complete Sessions** (Every hour)
   - Marks past sessions as completed
   - Updates session status

3. **Daily Summary** (8:00 AM)
   - Lists today's sessions
   - Sent to teacher only

4. **Absence Alerts** (Every 15 min)
   - Checks sessions that started 30 mins ago
   - Sends alert if student didn't attend
   - Sent to parent
