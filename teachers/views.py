"""
Teacher Views
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from accounts.permissions import IsTeacher
from .models import TeacherProfile, TeacherStats, TeacherNotificationSettings
from .serializers import (
    TeacherProfileSerializer, TeacherStatsSerializer,
    TeacherNotificationSettingsSerializer, TeacherDashboardSerializer
)


class TeacherProfileViewSet(viewsets.ModelViewSet):
    """Teacher profile management"""
    serializer_class = TeacherProfileSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return TeacherProfile.objects.filter(user=self.request.user)
    
    def get_object(self):
        profile, created = TeacherProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'center_name': self.request.user.center_name or 'My Center'
            }
        )
        return profile
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get teacher dashboard summary"""
        teacher = request.user
        today = timezone.now().date()
        
        # Student statistics
        students_qs = teacher.students.filter(is_active=True)
        total_students = students_qs.count()
        
        # Group statistics  
        groups_qs = teacher.teaching_groups.filter(is_active=True)
        total_groups = groups_qs.count()
        
        # Session statistics
        from teaching_sessions.models import Session
        today_sessions = Session.objects.filter(
            group__teacher=teacher,
            date=today,
            is_active=True
        ).count()
        
        # Payment statistics
        from payments.models import Payment
        this_month_start = today.replace(day=1)
        payments_qs = Payment.objects.filter(student__teacher=teacher)
        
        pending_payments = payments_qs.filter(
            status='pending'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        overdue_payments = payments_qs.filter(
            status='overdue'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        monthly_revenue = payments_qs.filter(
            status='paid',
            created_at__gte=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Attendance rate
        from attendance.models import Attendance
        this_month_attendance = Attendance.objects.filter(
            session__group__teacher=teacher,
            session__date__gte=this_month_start
        )
        
        total_attendance = this_month_attendance.count()
        present_count = this_month_attendance.filter(status='present').count()
        attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
        
        # Recent alerts
        from smart_insights.models import Alert
        recent_alerts = Alert.objects.filter(
            teacher=teacher,
            is_active=True
        ).order_by('-created_at')[:5].values(
            'id', 'title', 'message', 'severity', 'created_at'
        )
        
        # Upcoming sessions
        from teaching_sessions.models import Session
        upcoming_sessions = Session.objects.filter(
            group__teacher=teacher,
            date__gte=today,
            date__lte=today + timedelta(days=7),
            is_active=True
        ).select_related('group').order_by('date', 'start_time')[:10].values(
            'id', 'group__name', 'date', 'start_time', 'end_time'
        )
        
        dashboard_data = {
            'total_students': total_students,
            'active_students': total_students,  # All active students
            'total_groups': total_groups,
            'active_groups': total_groups,  # All active groups
            'today_sessions': today_sessions,
            'pending_payments': pending_payments,
            'overdue_payments': overdue_payments,
            'monthly_revenue': monthly_revenue,
            'attendance_rate': round(attendance_rate, 2),
            'recent_alerts': list(recent_alerts),
            'upcoming_sessions': list(upcoming_sessions),
        }
        
        serializer = TeacherDashboardSerializer(dashboard_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get teacher statistics"""
        teacher = request.user
        stat_type = request.query_params.get('type', 'daily')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = TeacherStats.objects.filter(
            teacher=teacher,
            stat_type=stat_type
        )
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        queryset = queryset.order_by('date')
        serializer = TeacherStatsSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get', 'put'])
    def notification_settings(self, request):
        """Get or update notification settings"""
        settings_obj, created = TeacherNotificationSettings.objects.get_or_create(
            teacher=request.user
        )
        
        if request.method == 'GET':
            serializer = TeacherNotificationSettingsSerializer(settings_obj)
            return Response(serializer.data)
        
        elif request.method == 'PUT':
            serializer = TeacherNotificationSettingsSerializer(
                settings_obj, 
                data=request.data, 
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def update_pin(self, request):
        """Update teacher PIN"""
        current_pin = request.data.get('current_pin')
        new_pin = request.data.get('new_pin')
        
        if not current_pin or not new_pin:
            return Response(
                {'error': 'Both current_pin and new_pin are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not request.user.check_teacher_pin(current_pin):
            return Response(
                {'error': 'Invalid current PIN'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_pin) < 4 or len(new_pin) > 10:
            return Response(
                {'error': 'PIN must be between 4 and 10 digits'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        request.user.set_teacher_pin(new_pin)
        request.user.save()
        
        return Response({'message': 'PIN updated successfully'})


class TeacherStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """Teacher statistics read-only viewset"""
    serializer_class = TeacherStatsSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return TeacherStats.objects.filter(teacher=self.request.user)