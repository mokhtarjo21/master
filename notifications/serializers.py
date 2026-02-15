"""
Notification Serializers
"""
from rest_framework import serializers
from .models import Notification, NotificationTemplate, NotificationLog, NotificationBatch


class NotificationSerializer(serializers.ModelSerializer):
    """Main notification serializer"""
    can_retry = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient_type', 'recipient_id', 'recipient_name',
            'recipient_phone', 'recipient_email', 'title', 'message',
            'notification_type', 'channel', 'status', 'scheduled_at',
            'sent_at', 'error_message', 'retry_count', 'max_retries',
            'metadata', 'can_retry', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'teacher', 'status', 'sent_at', 'error_message',
            'retry_count', 'created_at', 'updated_at'
        ]
    
    def get_can_retry(self, obj):
        return obj.can_retry()
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return Notification.objects.create(**validated_data)


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for notification creation"""
    
    class Meta:
        model = Notification
        fields = [
            'recipient_type', 'recipient_id', 'recipient_name',
            'recipient_phone', 'recipient_email', 'title', 'message',
            'notification_type', 'channel', 'scheduled_at', 'metadata'
        ]
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return Notification.objects.create(**validated_data)


class BulkNotificationSerializer(serializers.Serializer):
    """Serializer for bulk notification creation"""
    recipient_type = serializers.ChoiceField(choices=Notification.RECIPIENT_TYPES)
    recipient_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    title = serializers.CharField(max_length=200)
    message = serializers.DictField()
    notification_type = serializers.ChoiceField(choices=Notification.NOTIFICATION_TYPES)
    channel = serializers.ChoiceField(choices=Notification.CHANNELS, default='whatsapp')
    scheduled_at = serializers.DateTimeField(required=False)
    
    def validate(self, data):
        recipient_type = data.get('recipient_type')
        recipient_ids = data.get('recipient_ids', [])
        
        if recipient_type in ['student', 'parent'] and not recipient_ids:
            raise serializers.ValidationError("recipient_ids is required for student/parent notifications")
        
        return data


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Notification template serializer"""
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'notification_type', 'channel',
            'title_template', 'message_template', 'available_variables',
            'is_active', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return NotificationTemplate.objects.create(**validated_data)


class NotificationLogSerializer(serializers.ModelSerializer):
    """Notification log serializer"""
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'action', 'details', 'payload', 'success',
            'error_message', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NotificationBatchSerializer(serializers.ModelSerializer):
    """Notification batch serializer"""
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = NotificationBatch
        fields = [
            'id', 'name', 'description', 'status', 'total_notifications',
            'sent_notifications', 'failed_notifications', 'progress_percentage',
            'started_at', 'completed_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'teacher', 'status', 'total_notifications',
            'sent_notifications', 'failed_notifications', 'progress_percentage',
            'started_at', 'completed_at', 'created_at'
        ]
    
    def get_progress_percentage(self, obj):
        if obj.total_notifications > 0:
            processed = obj.sent_notifications + obj.failed_notifications
            return round((processed / obj.total_notifications) * 100, 2)
        return 0
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return NotificationBatch.objects.create(**validated_data)