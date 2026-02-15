"""
Subscriptions Serializers
"""
from rest_framework import serializers
from .models import SubscriptionPlan, TeacherSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Subscription plan serializer"""
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'description', 'price', 'billing_cycle',
            'max_students', 'max_groups', 'storage_gb',
            'features', 'is_active', 'is_popular'
        ]


class TeacherSubscriptionSerializer(serializers.ModelSerializer):
    """Teacher subscription serializer"""
    plan_details = SubscriptionPlanSerializer(source='plan', read_only=True)
    is_expired = serializers.SerializerMethodField()
    usage_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = TeacherSubscription
        fields = [
            'id', 'plan', 'plan_details', 'status',
            'start_date', 'end_date', 'auto_renew',
            'current_students', 'current_groups', 'storage_used_gb',
            'is_expired', 'usage_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_students', 'current_groups', 'storage_used_gb']
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_usage_percentage(self, obj):
        return {
            'students': (obj.current_students / obj.plan.max_students * 100) if obj.plan.max_students > 0 else 0,
            'groups': (obj.current_groups / obj.plan.max_groups * 100) if obj.plan.max_groups > 0 else 0,
            'storage': (float(obj.storage_used_gb) / obj.plan.storage_gb * 100) if obj.plan.storage_gb > 0 else 0,
        }
