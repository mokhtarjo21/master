"""
Settings App Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth.hashers import check_password, make_password
from django.http import JsonResponse, HttpResponse
from accounts.permissions import IsTeacher
from .models import AppSettings, DangerZoneAction
from .serializers import AppSettingsSerializer, DangerZoneActionSerializer
from .security_log import SecurityLog
import json
import io
import zipfile


class SettingsViewSet(viewsets.ViewSet):
    """Settings management viewset"""
    permission_classes = [IsTeacher]
    
    def list(self, request):
        """Get current settings"""
        settings, created = AppSettings.objects.get_or_create(teacher=request.user)
        serializer = AppSettingsSerializer(settings)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """Update settings"""
        settings, created = AppSettings.objects.get_or_create(teacher=request.user)
        serializer = AppSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def reset_data(self, request):
        """Danger zone: Reset/delete data"""
        serializer = DangerZoneActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reset_type = serializer.validated_data['reset_type']
        items_deleted = 0
        
        if reset_type == 'delete_students':
            from students.models import Student
            items_deleted = Student.objects.filter(teacher=request.user).count()
            Student.objects.filter(teacher=request.user).delete()
        
        elif reset_type == 'delete_sessions':
            from teaching_sessions.models import Session
            items_deleted = Session.objects.filter(group__teacher=request.user).count()
            Session.objects.filter(group__teacher=request.user).delete()
        
        elif reset_type == 'delete_payments':
            from payments.models import Payment
            items_deleted = Payment.objects.filter(student__teacher=request.user).count()
            Payment.objects.filter(student__teacher=request.user).delete()
        
        elif reset_type == 'delete_grades':
            from grades.models import Grade
            items_deleted = Grade.objects.filter(student__teacher=request.user).count()
            Grade.objects.filter(student__teacher=request.user).delete()
        
        elif reset_type == 'delete_all':
            from students.models import Student
            from groups.models import Group
            from teaching_sessions.models import Session
            from payments.models import Payment
            from grades.models import Grade
            
            items_deleted = (
                Student.objects.filter(teacher=request.user).count() +
                Group.objects.filter(teacher=request.user).count() +
                Session.objects.filter(group__teacher=request.user).count() +
                Payment.objects.filter(student__teacher=request.user).count() +
                Grade.objects.filter(student__teacher=request.user).count()
            )
            
            Student.objects.filter(teacher=request.user).delete()
            Group.objects.filter(teacher=request.user).delete()
            Session.objects.filter(group__teacher=request.user).delete()
            Payment.objects.filter(student__teacher=request.user).delete()
            Grade.objects.filter(student__teacher=request.user).delete()
        
        # Log the action
        DangerZoneAction.objects.create(
            teacher=request.user,
            action_type=reset_type,
            confirmation_text=serializer.validated_data['confirmation_text'],
            items_affected=items_deleted
        )
        
        return Response({
            'message': 'Data reset completed successfully',
            'reset_type': reset_type,
            'items_deleted': items_deleted,
            'timestamp': timezone.now()
        })
    
    @action(detail=False, methods=['post'])
    def change_pin(self, request):
        """Change teacher PIN"""
        old_pin = request.data.get('old_pin')
        new_pin = request.data.get('new_pin')
        confirm_pin = request.data.get('confirm_pin')
        
        if not all([old_pin, new_pin, confirm_pin]):
            return Response(
                {'error': 'old_pin, new_pin, and confirm_pin are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify new PIN matches confirmation
        if new_pin != confirm_pin:
            return Response(
                {'error': 'New PIN and confirmation do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate new PIN format (4 digits)
        if not new_pin.isdigit() or len(new_pin) != 4:
            return Response(
                {'error': 'PIN must be exactly 4 digits'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check old PIN
        if not check_password(old_pin, request.user.pin):
            # Log failed attempt
            SecurityLog.objects.create(
                teacher=request.user,
                event_type='pin_change_failed',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=False
            )
            return Response(
                {'error': 'Current PIN is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update PIN
        request.user.pin = make_password(new_pin)
        request.user.save()
        
        # Log successful change
        SecurityLog.objects.create(
            teacher=request.user,
            event_type='pin_change',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True
        )
        
        return Response({
            'message': 'PIN changed successfully',
            'timestamp': timezone.now()
        })
    
    @action(detail=False, methods=['get'])
    def export_data(self, request):
        """Export all teacher data as JSON"""
        from students.models import Student
        from groups.models import Group
        from teaching_sessions.models import Session
        from payments.models import Payment
        from grades.models import Grade
        from notifications.models import Notification
        
        # Collect all data
        data = {
            'exported_at': timezone.now().isoformat(),
            'teacher': {
                'username': request.user.username,
                'email': request.user.email,
            },
            'settings': AppSettingsSerializer(AppSettings.objects.get_or_create(teacher=request.user)[0]).data,
            'students': list(Student.objects.filter(teacher=request.user).values()),
            'groups': list(Group.objects.filter(teacher=request.user).values()),
            'sessions': list(Session.objects.filter(group__teacher=request.user).values()),
            'payments': list(Payment.objects.filter(student__teacher=request.user).values()),
            'grades': list(Grade.objects.filter(student__teacher=request.user).values()),
            'notifications': list(Notification.objects.filter(teacher=request.user).values()),
        }
        
        # Log export action
        SecurityLog.objects.create(
            teacher=request.user,
            event_type='data_export',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'total_records': sum([
                len(data['students']),
                len(data['groups']),
                len(data['sessions']),
                len(data['payments']),
                len(data['grades'])
            ])}
        )
        
        # Create JSON file
        response = HttpResponse(
            json.dumps(data, indent=2, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="teacher_data_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
        
        return response
