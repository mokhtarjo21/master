"""
Rules Engine Views
"""
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from django_filters.rest_framework import DjangoFilterBackend
import time

from accounts.permissions import IsTeacher
from .models import Rule, RuleExecution, RuleTemplate, RuleSet
from .serializers import (
    RuleSerializer, RuleCreateSerializer, RuleExecutionSerializer,
    RuleTemplateSerializer, RuleSetSerializer, RuleTestSerializer
)


class RuleViewSet(viewsets.ModelViewSet):
    """Rule management viewset"""
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rule_type', 'trigger_event', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['priority', 'name', 'created_at']
    ordering = ['priority', 'name']
    
    def get_queryset(self):
        return Rule.objects.filter(teacher=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RuleCreateSerializer
        return RuleSerializer
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test rule with sample data"""
        rule = self.get_object()
        serializer = RuleTestSerializer(data=request.data)
        
        if serializer.is_valid():
            test_data = serializer.validated_data['test_data']
            
            start_time = time.time()
            
            # Evaluate conditions
            conditions_met = rule.evaluate_conditions(test_data)
            
            # Execute actions if conditions are met
            actions_executed = []
            if conditions_met:
                actions_executed = rule.execute_actions(test_data)
            
            execution_time = time.time() - start_time
            
            return Response({
                'rule_triggered': conditions_met,
                'actions_executed': actions_executed,
                'test_results': {
                    'conditions_met': conditions_met,
                    'execution_time': f"{execution_time:.2f}s"
                }
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle rule active status"""
        rule = self.get_object()
        rule.is_active = not rule.is_active
        rule.save()
        
        serializer = RuleSerializer(rule)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_toggle(self, request):
        """Bulk toggle rule active status"""
        rule_ids = request.data.get('rule_ids', [])
        active = request.data.get('active', True)
        
        if not rule_ids:
            return Response(
                {'error': 'rule_ids is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rules = self.get_queryset().filter(id__in=rule_ids)
        updated_count = rules.update(is_active=active)
        
        return Response({
            'message': f'Updated {updated_count} rules',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get rule statistics"""
        queryset = self.get_queryset()
        
        stats = queryset.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            inactive=Count('id', filter=Q(is_active=False))
        )
        
        # Rule type breakdown
        type_stats = queryset.values('rule_type').annotate(
            count=Count('id')
        ).order_by('rule_type')
        
        # Trigger event breakdown
        trigger_stats = queryset.values('trigger_event').annotate(
            count=Count('id')
        ).order_by('trigger_event')
        
        # Recent executions
        recent_executions = RuleExecution.objects.filter(
            rule__teacher=request.user,
            executed_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        stats.update({
            'by_type': list(type_stats),
            'by_trigger': list(trigger_stats),
            'recent_executions': recent_executions
        })
        
        return Response(stats)


class RuleExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """Rule execution history"""
    serializer_class = RuleExecutionSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['rule', 'trigger_event', 'execution_status']
    ordering_fields = ['executed_at', 'execution_time']
    ordering = ['-executed_at']
    
    def get_queryset(self):
        return RuleExecution.objects.filter(rule__teacher=self.request.user)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent executions"""
        days = int(request.query_params.get('days', 7))
        since_date = timezone.now() - timedelta(days=days)
        
        queryset = self.get_queryset().filter(executed_at__gte=since_date)
        serializer = RuleExecutionSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def failed(self, request):
        """Get failed executions"""
        queryset = self.get_queryset().filter(execution_status='failed')
        serializer = RuleExecutionSerializer(queryset, many=True)
        return Response(serializer.data)


class RuleTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """Rule template management"""
    serializer_class = RuleTemplateSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['category', 'name']
    ordering = ['category', 'name']
    
    def get_queryset(self):
        return RuleTemplate.objects.filter(is_active=True)
    
    @action(detail=True, methods=['post'])
    def create_rule(self, request, pk=None):
        """Create rule from template"""
        template = self.get_object()
        customizations = request.data.get('customizations', {})
        
        try:
            rule = template.create_rule_for_teacher(request.user, customizations)
            serializer = RuleSerializer(rule)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': f'Failed to create rule: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class RuleSetViewSet(viewsets.ModelViewSet):
    """Rule set management"""
    serializer_class = RuleSetSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        return RuleSet.objects.filter(teacher=self.request.user)
    
    @action(detail=True, methods=['get'])
    def rules(self, request, pk=None):
        """Get rules in the set"""
        rule_set = self.get_object()
        rules = rule_set.get_rules()
        
        serializer = RuleSerializer(rules, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute rule set with trigger event"""
        rule_set = self.get_object()
        trigger_event = request.data.get('trigger_event')
        context = request.data.get('context', {})
        
        if not trigger_event:
            return Response(
                {'error': 'trigger_event is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            results = rule_set.execute_rules(trigger_event, context)
            return Response({
                'message': f'Executed rule set: {rule_set.name}',
                'results': results
            })
        except Exception as e:
            return Response(
                {'error': f'Rule set execution failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )