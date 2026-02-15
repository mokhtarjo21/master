"""
Settings App Serializers
"""
from rest_framework import serializers
from .models import AppSettings, DangerZoneAction


class AppSettingsSerializer(serializers.ModelSerializer):
    """App settings serializer"""
    subscription = serializers.SerializerMethodField()
    
    class Meta:
        model = AppSettings
        fields = [
            'id', 'center_name', 'teacher_name', 'logo',
            'language', 'theme', 'currency', 'timezone',
            'email_enabled', 'whatsapp_enabled', 'push_enabled', 'sms_enabled',
            'attendance_alerts', 'payment_alerts', 'grade_alerts',
            'low_attendance_rate', 'consecutive_absences', 'overdue_payment_days', 'low_grade_threshold',
            'subscription', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_subscription(self, obj):
        # TODO: Get from subscriptions app
        return {
            'plan': 'premium',
            'max_students': 100,
            'max_groups': 20,
            'expires_at': None
        }


class DangerZoneActionSerializer(serializers.Serializer):
    """Danger zone action serializer"""
    reset_type = serializers.ChoiceField(choices=DangerZoneAction.RESET_TYPES)
    confirmation_text = serializers.CharField(max_length=200)
    
    def validate(self, data):
        reset_type = data['reset_type']
        confirmation = data['confirmation_text']
        
        # Validate confirmation text
        expected_texts = {
            'delete_students': 'DELETE ALL STUDENTS',
            'delete_sessions': 'DELETE ALL SESSIONS',
            'delete_payments': 'DELETE ALL PAYMENTS',
            'delete_grades': 'DELETE ALL GRADES',
            'delete_all': 'DELETE ALL DATA',
        }
        
        if confirmation != expected_texts.get(reset_type):
            raise serializers.ValidationError(
                f"Confirmation text must be exactly: {expected_texts.get(reset_type)}"
            )
        
        return data
