"""
Audit Logs Views
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from accounts.permissions import IsTeacher
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Audit log viewset"""
    serializer_class = AuditLogSerializer
    permission_classes = [IsTeacher]
    filterset_fields = ['action', 'model_name']
    search_fields = ['object_repr', 'user__username']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        # Teachers can only see their own audit logs
        return AuditLog.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def activity_summary(self, request):
        """Get activity summary"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = self.get_queryset()
        
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)
        
        # Aggregate by action
        by_action = queryset.values('action').annotate(count=Count('id'))
        
        # Aggregate by model
        by_model = queryset.values('model_name').annotate(count=Count('id'))
        
        # Most active days
        most_active_days = queryset.extra(
            select={'day': 'DATE(timestamp)'}
        ).values('day').annotate(
            actions=Count('id')
        ).order_by('-actions')[:5]
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'total_actions': queryset.count(),
            'by_action': {item['action']: item['count'] for item in by_action},
            'by_model': {item['model_name']: item['count'] for item in by_model if item['model_name']},
            'most_active_days': list(most_active_days)
        })
