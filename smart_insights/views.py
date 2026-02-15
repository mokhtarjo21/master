"""
Smart Insights Views
"""
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import date, timedelta
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsTeacher
from .models import Insight, Alert, Suggestion, AnalyticsSnapshot, DashboardWidget
from .serializers import (
    InsightSerializer, AlertSerializer, SuggestionSerializer,
    AnalyticsSnapshotSerializer, DashboardWidgetSerializer,
    DashboardDataSerializer
)


class InsightViewSet(viewsets.ModelViewSet):
    """Smart insights management"""
    serializer_class = InsightSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'priority', 'is_active', 'action_taken']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Insight.objects.filter(teacher=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_action_taken(self, request, pk=None):
        """Mark insight as acted upon"""
        insight = self.get_object()
        notes = request.data.get('notes', '')
        
        insight.mark_action_taken(notes)
        
        serializer = InsightSerializer(insight)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def high_priority(self, request):
        """Get high priority insights"""
        queryset = self.get_queryset().filter(
            priority__in=['high', 'critical'],
            is_active=True,
            action_taken=False
        )
        serializer = InsightSerializer(queryset, many=True)
        return Response(serializer.data)


class AlertViewSet(viewsets.ModelViewSet):
    """Alert management"""
    serializer_class = AlertSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['alert_type', 'severity', 'is_active', 'is_resolved']
    search_fields = ['title', 'message', 'target_name']
    ordering_fields = ['created_at', 'severity']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Alert.objects.filter(teacher=self.request.user)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an alert"""
        alert = self.get_object()
        notes = request.data.get('notes', '')
        
        alert.resolve(resolved_by=request.user, notes=notes)
        
        serializer = AlertSerializer(alert)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_resolve(self, request):
        """Bulk resolve alerts"""
        alert_ids = request.data.get('alert_ids', [])
        notes = request.data.get('notes', '')
        
        if not alert_ids:
            return Response(
                {'error': 'alert_ids is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        alerts = self.get_queryset().filter(
            id__in=alert_ids,
            is_active=True,
            is_resolved=False
        )
        
        resolved_count = 0
        for alert in alerts:
            alert.resolve(resolved_by=request.user, notes=notes)
            resolved_count += 1
        
        return Response({
            'message': f'Resolved {resolved_count} alerts',
            'resolved_count': resolved_count
        })
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active unresolved alerts"""
        queryset = self.get_queryset().filter(
            is_active=True,
            is_resolved=False
        )
        serializer = AlertSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def critical(self, request):
        """Get critical alerts"""
        queryset = self.get_queryset().filter(
            severity='critical',
            is_active=True,
            is_resolved=False
        )
        serializer = AlertSerializer(queryset, many=True)
        return Response(serializer.data)


class SuggestionViewSet(viewsets.ModelViewSet):
    """Suggestion management"""
    serializer_class = SuggestionSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'priority', 'effort_level', 'is_active', 'is_implemented']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Suggestion.objects.filter(teacher=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_implemented(self, request, pk=None):
        """Mark suggestion as implemented"""
        suggestion = self.get_object()
        notes = request.data.get('notes', '')
        
        suggestion.mark_implemented(notes)
        
        serializer = SuggestionSerializer(suggestion)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def quick_wins(self, request):
        """Get low effort, high impact suggestions"""
        queryset = self.get_queryset().filter(
            effort_level='low',
            priority__in=['high', 'medium'],
            is_active=True,
            is_implemented=False
        )
        serializer = SuggestionSerializer(queryset, many=True)
        return Response(serializer.data)


class AnalyticsViewSet(viewsets.ViewSet):
    """Analytics and dashboard data"""
    permission_classes = [IsTeacher]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard analytics data"""
        teacher = request.user
        
        # Get date range
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Student metrics
        from students.models import Student
        students = Student.objects.filter(teacher=teacher, is_active=True)
        total_students = students.count()
        new_students = students.filter(created_at__gte=start_date).count()
        
        # Financial metrics
        from payments.models import Payment
        payments = Payment.objects.filter(student__teacher=teacher)
        total_revenue = payments.filter(
            status='paid',
            payment_date__gte=start_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        pending_payments = payments.filter(status='pending').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Attendance metrics
        from attendance.models import Attendance
        attendance = Attendance.objects.filter(
            session__group__teacher=teacher,
            session__date__gte=start_date
        )
        
        total_attendance = attendance.count()
        present_count = attendance.filter(status='present').count()
        attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
        
        # Session metrics
        from teaching_sessions.models import Session
        sessions = Session.objects.filter(
            group__teacher=teacher,
            date__gte=start_date
        )
        total_sessions = sessions.count()
        completed_sessions = sessions.filter(status='completed').count()
        
        # Alert metrics
        active_alerts = Alert.objects.filter(
            teacher=teacher,
            is_active=True,
            is_resolved=False
        ).count()
        
        dashboard_data = {
            'overview': {
                'total_students': total_students,
                'new_students': new_students,
                'total_revenue': float(total_revenue),
                'pending_payments': float(pending_payments),
                'attendance_rate': round(attendance_rate, 2),
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'active_alerts': active_alerts
            },
            'trends': self._get_trends(teacher, start_date, end_date),
            'alerts_summary': self._get_alerts_summary(teacher),
            'top_insights': self._get_top_insights(teacher)
        }
        
        serializer = DashboardDataSerializer(dashboard_data)
        return Response(serializer.data)
    
    def _get_trends(self, teacher, start_date, end_date):
        """Get trend data for charts"""
        # Daily revenue trend
        from payments.models import Payment
        from django.db.models import Sum
        from django.db.models.functions import TruncDate
        
        revenue_trend = Payment.objects.filter(
            student__teacher=teacher,
            status='paid',
            payment_date__gte=start_date,
            payment_date__lte=end_date
        ).annotate(
            date=TruncDate('payment_date')
        ).values('date').annotate(
            amount=Sum('amount')
        ).order_by('date')
        
        # Student growth trend
        from students.models import Student
        student_trend = Student.objects.filter(
            teacher=teacher,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return {
            'revenue': list(revenue_trend),
            'students': list(student_trend)
        }
    
    def _get_alerts_summary(self, teacher):
        """Get alerts summary"""
        alerts = Alert.objects.filter(teacher=teacher, is_active=True, is_resolved=False)
        
        return {
            'total_active': alerts.count(),
            'critical': alerts.filter(severity='critical').count(),
            'high': alerts.filter(severity='error').count(),
            'medium': alerts.filter(severity='warning').count(),
            'by_type': list(alerts.values('alert_type').annotate(
                count=Count('id')
            ).order_by('-count')[:5])
        }
    
    def _get_top_insights(self, teacher):
        """Get top insights"""
        insights = Insight.objects.filter(
            teacher=teacher,
            is_active=True,
            action_taken=False
        ).order_by('-priority', '-created_at')[:5]
        
        from .serializers import InsightSerializer
        return InsightSerializer(insights, many=True).data


class DashboardWidgetViewSet(viewsets.ModelViewSet):
    """Dashboard widget management"""
    serializer_class = DashboardWidgetSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['widget_type', 'is_active']
    ordering_fields = ['position_y', 'position_x']
    ordering = ['position_y', 'position_x']
    
    def get_queryset(self):
        return DashboardWidget.objects.filter(teacher=self.request.user)
    
    @action(detail=False, methods=['post'])
    def update_layout(self, request):
        """Update widget layout positions"""
        widgets_data = request.data.get('widgets', [])
        
        for widget_data in widgets_data:
            widget_id = widget_data.get('id')
            position_x = widget_data.get('position_x')
            position_y = widget_data.get('position_y')
            width = widget_data.get('width')
            height = widget_data.get('height')
            
            try:
                widget = self.get_queryset().get(id=widget_id)
                if position_x is not None:
                    widget.position_x = position_x
                if position_y is not None:
                    widget.position_y = position_y
                if width is not None:
                    widget.width = width
                if height is not None:
                    widget.height = height
                widget.save()
            except DashboardWidget.DoesNotExist:
                continue
        
        return Response({'message': 'Layout updated successfully'})