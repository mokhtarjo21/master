"""
Subscriptions Serializers
"""
from rest_framework import serializers
from .models import SubscriptionPlan, TeacherSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Public plan serializer (read-only for teachers)"""
    subscribers_count = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'name_ar', 'description', 'price',
            'billing_cycle', 'duration_days',
            'max_students', 'max_groups', 'storage_gb',
            'features', 'is_active', 'is_popular',
            'subscribers_count', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_subscribers_count(self, obj):
        return obj.subscriptions.filter(status='active').count()


class AdminSubscriptionPlanSerializer(serializers.ModelSerializer):
    """Full CRUD serializer — admin only"""
    subscribers_count = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'name_ar', 'description', 'price',
            'billing_cycle', 'duration_days',
            'max_students', 'max_groups', 'storage_gb',
            'features', 'is_active', 'is_popular',
            'subscribers_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'subscribers_count']

    def get_subscribers_count(self, obj):
        return obj.subscriptions.filter(status='active').count()

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Price must be a positive number.')
        return value

    def validate_duration_days(self, value):
        if value < 0:
            raise serializers.ValidationError('Duration days must be 0 (lifetime) or positive.')
        return value

    def validate_features(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Features must be a list of strings.')
        return value


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


class TeacherSubscriptionAdminSerializer(serializers.ModelSerializer):
    """Admin serializer — assign/modify teacher subscriptions"""
    plan_details = SubscriptionPlanSerializer(source='plan', read_only=True)
    teacher_username = serializers.CharField(source='teacher.username', read_only=True)
    teacher_email = serializers.CharField(source='teacher.email', read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = TeacherSubscription
        fields = [
            'id', 'teacher', 'teacher_username', 'teacher_email',
            'plan', 'plan_details', 'status',
            'start_date', 'end_date', 'auto_renew',
            'current_students', 'current_groups',
            'is_expired', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'current_students', 'current_groups', 'created_at', 'updated_at']

    def get_is_expired(self, obj):
        return obj.is_expired()
