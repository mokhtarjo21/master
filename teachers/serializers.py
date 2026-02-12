"""
Teacher Serializers
"""
from rest_framework import serializers
from .models import TeacherProfile, TeacherStats, TeacherNotificationSettings


class TeacherProfileSerializer(serializers.ModelSerializer):
    """Teacher profile serializer"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', required=False)
    
    class Meta:
        model = TeacherProfile
        fields = [
            'id', 'username', 'email', 'center_name', 'center_address',
            'phone_number', 'whatsapp_number', 'subscription_plan',
            'max_students', 'max_groups', 'default_language', 'timezone',
            'currency', 'default_session_price', 'default_monthly_price',
            'email_notifications', 'whatsapp_notifications', 'push_notifications',
            'smart_insights_enabled', 'auto_alerts_enabled', 'auto_receipts_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'username', 'created_at', 'updated_at']
    
    def update(self, instance, validated_data):
        # Handle user email update
        user_data = validated_data.pop('user', {})
        if 'email' in user_data:
            instance.user.email = user_data['email']
            instance.user.save()
        
        return super().update(instance, validated_data)


class TeacherStatsSerializer(serializers.ModelSerializer):
    """Teacher statistics serializer"""
    attendance_rate = serializers.SerializerMethodField()
    revenue_growth = serializers.SerializerMethodField()
    
    class Meta:
        model = TeacherStats
        fields = [
            'id', 'date', 'stat_type', 'total_students', 'active_students',
            'new_students', 'total_groups', 'active_groups', 'total_sessions',
            'completed_sessions', 'cancelled_sessions', 'total_revenue',
            'pending_payments', 'overdue_payments', 'total_attendance',
            'present_count', 'absent_count', 'late_count', 'attendance_rate',
            'revenue_growth', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_attendance_rate(self, obj):
        if obj.total_attendance > 0:
            return round((obj.present_count / obj.total_attendance) * 100, 2)
        return 0
    
    def get_revenue_growth(self, obj):
        # Calculate revenue growth compared to previous period
        previous_stat = TeacherStats.objects.filter(
            teacher=obj.teacher,
            stat_type=obj.stat_type,
            date__lt=obj.date
        ).order_by('-date').first()
        
        if previous_stat and previous_stat.total_revenue > 0:
            growth = ((obj.total_revenue - previous_stat.total_revenue) / previous_stat.total_revenue) * 100
            return round(growth, 2)
        return 0


class TeacherNotificationSettingsSerializer(serializers.ModelSerializer):
    """Teacher notification settings serializer"""
    
    class Meta:
        model = TeacherNotificationSettings
        fields = [
            'id', 'payment_received_email', 'payment_received_whatsapp',
            'payment_overdue_email', 'payment_overdue_whatsapp',
            'session_reminder_email', 'session_reminder_whatsapp',
            'session_cancelled_email', 'session_cancelled_whatsapp',
            'new_student_email', 'student_absence_email', 'student_absence_whatsapp',
            'smart_alerts_email', 'smart_alerts_whatsapp',
            'system_updates_email', 'backup_completion_email',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TeacherDashboardSerializer(serializers.Serializer):
    """Teacher dashboard summary data"""
    total_students = serializers.IntegerField()
    active_students = serializers.IntegerField()
    total_groups = serializers.IntegerField()
    active_groups = serializers.IntegerField()
    today_sessions = serializers.IntegerField()
    pending_payments = serializers.DecimalField(max_digits=10, decimal_places=2)
    overdue_payments = serializers.DecimalField(max_digits=10, decimal_places=2)
    monthly_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    attendance_rate = serializers.FloatField()
    recent_alerts = serializers.ListField()
    upcoming_sessions = serializers.ListField()