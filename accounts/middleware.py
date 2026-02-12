"""
Authentication Middleware
"""
from django.utils import timezone
from django.conf import settings
from .models import TeacherSession


class LastActivityMiddleware:
    """Track user last activity"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Update last activity for authenticated users
        if request.user.is_authenticated:
            request.user.last_activity = timezone.now()
            request.user.save(update_fields=['last_activity'])
            
            # Check teacher session expiry
            if request.user.user_type == 'teacher':
                active_session = TeacherSession.objects.filter(
                    teacher=request.user,
                    is_active=True,
                    expires_at__gt=timezone.now()
                ).first()
                
                if not active_session:
                    request.user.is_active_session = False
                    request.user.save(update_fields=['is_active_session'])

        response = self.get_response(request)
        return response