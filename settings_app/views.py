"""
Settings App Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from accounts.permissions import IsTeacher
from .models import AppSettings, DangerZoneAction
from .serializers import AppSettingsSerializer, DangerZoneActionSerializer


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
