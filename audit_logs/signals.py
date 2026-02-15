"""
Audit Logs Signals
Auto-log model changes
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from .models import AuditLog
import threading

# Thread-local storage for request data
_thread_locals = threading.local()


def set_current_request(request):
    """Store current request in thread-local storage"""
    _thread_locals.request = request


def get_current_request():
    """Get current request from thread-local storage"""
    return getattr(_thread_locals, 'request', None)


def get_client_ip(request):
    """Get client IP from request"""
    if not request:
        return None
    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Get user agent from request"""
    if not request:
        return ''
    return request.META.get('HTTP_USER_AGENT', '')


def should_log_model(sender):
    """Determine if model should be logged"""
    # Only log specific apps
    app_label = sender._meta.app_label
    logged_apps = [
        'students', 'payments', 'groups', 'teaching_sessions',
        'attendance', 'grades', 'receipts', 'parents'
    ]
    return app_label in logged_apps


@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    """Auto-log model saves"""
    if not should_log_model(sender):
        return
    
    # Avoid logging AuditLog itself
    if sender.__name__ == 'AuditLog':
        return
    
    request = get_current_request()
    user = getattr(request, 'user', None) if request else None
    
    # Skip if no user (e.g., management commands)
    if not user or not user.is_authenticated:
        return
    
    try:
        AuditLog.objects.create(
            user=user,
            action='create' if created else 'update',
            model_name=sender.__name__,
            object_id=str(instance.pk),
            object_repr=str(instance)[:200],  # Limit length
            changes={
                'created': created,
                'model': sender.__name__,
                'pk': str(instance.pk)
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
    except Exception as e:
        # Don't break the main operation if logging fails
        print(f"[AuditLog] Failed to log {sender.__name__}: {e}")


@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    """Auto-log model deletes"""
    if not should_log_model(sender):
        return
    
    if sender.__name__ == 'AuditLog':
        return
    
    request = get_current_request()
    user = getattr(request, 'user', None) if request else None
    
    if not user or not user.is_authenticated:
        return
    
    try:
        AuditLog.objects.create(
            user=user,
            action='delete',
            model_name=sender.__name__,
            object_id=str(instance.pk),
            object_repr=str(instance)[:200],
            changes={
                'deleted': True,
                'model': sender.__name__,
                'pk': str(instance.pk)
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
    except Exception as e:
        print(f"[AuditLog] Failed to log delete {sender.__name__}: {e}")


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log user login"""
    try:
        AuditLog.objects.create(
            user=user,
            action='login',
            model_name='User',
            object_id=str(user.pk),
            object_repr=user.username,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
    except Exception as e:
        print(f"[AuditLog] Failed to log login: {e}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout"""
    if not user:
        return
    
    try:
        AuditLog.objects.create(
            user=user,
            action='logout',
            model_name='User',
            object_id=str(user.pk),
            object_repr=user.username,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
    except Exception as e:
        print(f"[AuditLog] Failed to log logout: {e}")
