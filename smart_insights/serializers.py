"""
Smart Insights Serializers
"""
from rest_framework import serializers
from .models import Insight, Alert, Suggestion, AnalyticsSnapshot, DashboardWidget


class InsightSerializer(serializers.ModelSerializer):
    """Insight serializer"""
    
    class Meta:
        model = Insight
        fields = [
            'id', 'category', 'priority', 'title', 'description',
            'insight_data', 'recommendations', 'is_active',
            'action_taken', 'action_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return Insight.objects.create(**validated_data)


class AlertSerializer(serializers.ModelSerializer):
    """Alert serializer"""
    resolved_by_name = serializers.CharField(source='resolved_by.username', read_only=True)
    
    class Meta:
        model = Alert
        fields = [
            'id', 'alert_type', 'severity', 'title', 'message',
            'target_type', 'target_id', 'target_name', 'trigger_data',
            'suggested_actions', 'is_active', 'is_resolved',
            'resolved_at', 'resolved_by', 'resolved_by_name',
            'resolution_notes', 'created_at'
        ]
        read_only_fields = [
            'id', 'teacher', 'resolved_at', 'resolved_by',
            'resolved_by_name', 'created_at'
        ]
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return Alert.objects.create(**validated_data)


class SuggestionSerializer(serializers.ModelSerializer):
    """Suggestion serializer"""
    
    class Meta:
        model = Suggestion
        fields = [
            'id', 'category', 'priority', 'title', 'description',
            'implementation_steps', 'expected_impact', 'effort_level',
            'analysis_data', 'is_active', 'is_implemented',
            'implementation_date', 'implementation_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'teacher', 'implementation_date', 'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return Suggestion.objects.create(**validated_data)


class AnalyticsSnapshotSerializer(serializers.ModelSerializer):
    """Analytics snapshot serializer"""
    
    class Meta:
        model = AnalyticsSnapshot
        fields = [
            'id', 'snapshot_type', 'snapshot_date', 'total_students',
            'active_students', 'new_students', 'churned_students',
            'total_revenue', 'pending_payments', 'overdue_payments',
            'total_sessions', 'attendance_rate', 'punctuality_rate',
            'average_grade', 'grade_improvement', 'notification_open_rate',
            'parent_engagement_rate', 'metrics_data', 'created_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at']
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return AnalyticsSnapshot.objects.create(**validated_data)


class DashboardWidgetSerializer(serializers.ModelSerializer):
    """Dashboard widget serializer"""
    
    class Meta:
        model = DashboardWidget
        fields = [
            'id', 'title', 'widget_type', 'description', 'config',
            'data_source', 'refresh_interval', 'position_x', 'position_y',
            'width', 'height', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return DashboardWidget.objects.create(**validated_data)


class DashboardDataSerializer(serializers.Serializer):
    """Dashboard data serializer"""
    overview = serializers.DictField()
    trends = serializers.DictField()
    alerts_summary = serializers.DictField()
    top_insights = serializers.ListField()