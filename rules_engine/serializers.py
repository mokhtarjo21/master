"""
Rules Engine Serializers
"""
from rest_framework import serializers
from .models import Rule, RuleExecution, RuleTemplate, RuleSet


class RuleSerializer(serializers.ModelSerializer):
    """Rule serializer"""
    execution_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Rule
        fields = [
            'id', 'name', 'description', 'rule_type', 'trigger_event',
            'conditions', 'actions', 'priority', 'is_active',
            'last_executed', 'execution_count', 'execution_summary',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'teacher', 'last_executed', 'execution_count',
            'created_at', 'updated_at'
        ]
    
    def get_execution_summary(self, obj):
        recent_executions = obj.executions.filter(
            executed_at__gte=timezone.now() - timedelta(days=30)
        )
        
        return {
            'total_executions': obj.execution_count,
            'recent_executions': recent_executions.count(),
            'success_rate': self._calculate_success_rate(recent_executions)
        }
    
    def _calculate_success_rate(self, executions):
        if not executions.exists():
            return 0
        
        successful = executions.filter(execution_status='success').count()
        return round((successful / executions.count()) * 100, 2)
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return Rule.objects.create(**validated_data)


class RuleCreateSerializer(serializers.ModelSerializer):
    """Simplified rule creation serializer"""
    
    class Meta:
        model = Rule
        fields = [
            'name', 'description', 'rule_type', 'trigger_event',
            'conditions', 'actions', 'priority', 'is_active'
        ]
    
    def validate_conditions(self, value):
        """Validate conditions structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Conditions must be a dictionary")
        return value
    
    def validate_actions(self, value):
        """Validate actions structure"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Actions must be a list")
        
        for action in value:
            if not isinstance(action, dict) or 'type' not in action:
                raise serializers.ValidationError("Each action must be a dictionary with a 'type' field")
        
        return value
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return Rule.objects.create(**validated_data)


class RuleExecutionSerializer(serializers.ModelSerializer):
    """Rule execution serializer"""
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    
    class Meta:
        model = RuleExecution
        fields = [
            'id', 'rule', 'rule_name', 'trigger_event', 'trigger_data',
            'conditions_met', 'actions_executed', 'execution_status',
            'execution_time', 'executed_at'
        ]
        read_only_fields = ['id', 'executed_at']


class RuleTemplateSerializer(serializers.ModelSerializer):
    """Rule template serializer"""
    
    class Meta:
        model = RuleTemplate
        fields = [
            'id', 'name', 'description', 'category', 'template_config',
            'default_conditions', 'default_actions', 'customizable_fields',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RuleSetSerializer(serializers.ModelSerializer):
    """Rule set serializer"""
    rules_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RuleSet
        fields = [
            'id', 'name', 'description', 'execution_order',
            'is_active', 'rules_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at']
    
    def get_rules_count(self, obj):
        return obj.get_rules().count()
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return RuleSet.objects.create(**validated_data)


class RuleTestSerializer(serializers.Serializer):
    """Serializer for testing rules"""
    test_data = serializers.DictField()
    
    def validate_test_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Test data must be a dictionary")
        return value