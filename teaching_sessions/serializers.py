"""
Session Serializers
"""
from rest_framework import serializers
from .models import Session, SessionReminder, SessionMaterial, SessionNote


class SessionReminderSerializer(serializers.ModelSerializer):
    """Session reminder serializer"""
    
    class Meta:
        model = SessionReminder
        fields = [
            'id', 'reminder_type', 'reminder_time', 'title', 'message',
            'is_sent', 'sent_at', 'created_at'
        ]
        read_only_fields = ['id', 'is_sent', 'sent_at', 'created_at']


class SessionMaterialSerializer(serializers.ModelSerializer):
    """Session material serializer"""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = SessionMaterial
        fields = [
            'id', 'title', 'description', 'file', 'file_url',
            'external_link', 'usage_notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class SessionNoteSerializer(serializers.ModelSerializer):
    """Session note serializer"""
    
    class Meta:
        model = SessionNote
        fields = [
            'id', 'title', 'content', 'note_type',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SessionSerializer(serializers.ModelSerializer):
    """Main session serializer"""
    group_name = serializers.CharField(source='group.name', read_only=True)
    attendance_rate = serializers.SerializerMethodField()
    can_take_attendance = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = [
            'id', 'group', 'group_name', 'title', 'description',
            'date', 'start_time', 'end_time', 'status',
            'actual_start_time', 'actual_end_time', 'repeat_type',
            'repeat_until', 'repeat_count', 'lesson_content',
            'homework_assigned', 'materials_used', 'total_students',
            'present_count', 'absent_count', 'late_count',
            'attendance_rate', 'can_take_attendance', 'duration_minutes',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_students', 'present_count', 'absent_count',
            'late_count', 'actual_start_time', 'actual_end_time',
            'created_at', 'updated_at'
        ]
    
    def get_attendance_rate(self, obj):
        if obj.total_students > 0:
            return round((obj.present_count / obj.total_students) * 100, 2)
        return 0
    
    def get_can_take_attendance(self, obj):
        return obj.can_take_attendance()
    
    def get_duration_minutes(self, obj):
        if obj.start_time and obj.end_time:
            start_minutes = obj.start_time.hour * 60 + obj.start_time.minute
            end_minutes = obj.end_time.hour * 60 + obj.end_time.minute
            return end_minutes - start_minutes
        return 0
    
    def validate(self, data):
        # Validate time range
        if data.get('start_time') and data.get('end_time'):
            if data['start_time'] >= data['end_time']:
                raise serializers.ValidationError("End time must be after start time")
        
        # Validate repeat configuration
        repeat_type = data.get('repeat_type', 'none')
        if repeat_type != 'none':
            if not data.get('repeat_until') and not data.get('repeat_count'):
                raise serializers.ValidationError(
                    "Either repeat_until or repeat_count must be specified for repeating sessions"
                )
        
        return data


class SessionCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for session creation"""
    
    class Meta:
        model = Session
        fields = [
            'group', 'title', 'description', 'date', 'start_time',
            'end_time', 'repeat_type', 'repeat_until', 'repeat_count',
            'lesson_content', 'homework_assigned', 'materials_used'
        ]
    
    def validate(self, data):
        # Ensure teacher owns the group
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            group = data.get('group')
            if group and group.teacher != request.user:
                raise serializers.ValidationError("You can only create sessions for your own groups")
        
        # Validate time range
        if data.get('start_time') and data.get('end_time'):
            if data['start_time'] >= data['end_time']:
                raise serializers.ValidationError("End time must be after start time")
        
        return data


class SessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for session lists"""
    group_name = serializers.CharField(source='group.name', read_only=True)
    group_type = serializers.CharField(source='group.group_type', read_only=True)
    attendance_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = [
            'id', 'group_name', 'group_type', 'title', 'date',
            'start_time', 'end_time', 'status', 'attendance_summary'
        ]
    
    def get_attendance_summary(self, obj):
        return {
            'total': obj.total_students,
            'present': obj.present_count,
            'absent': obj.absent_count,
            'late': obj.late_count,
            'rate': round((obj.present_count / obj.total_students) * 100, 2) if obj.total_students > 0 else 0
        }


class SessionDetailSerializer(serializers.ModelSerializer):
    """Detailed session serializer with all related data"""
    group_detail = serializers.SerializerMethodField()
    attendance_list = serializers.SerializerMethodField()
    reminders = SessionReminderSerializer(many=True, read_only=True)
    session_materials = SessionMaterialSerializer(many=True, read_only=True)
    notes = SessionNoteSerializer(many=True, read_only=True)
    statistics = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = [
            'id', 'group', 'group_detail', 'title', 'description',
            'date', 'start_time', 'end_time', 'status',
            'actual_start_time', 'actual_end_time', 'repeat_type',
            'repeat_until', 'repeat_count', 'lesson_content',
            'homework_assigned', 'materials_used', 'total_students',
            'present_count', 'absent_count', 'late_count',
            'attendance_list', 'reminders', 'session_materials',
            'notes', 'statistics', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_students', 'present_count', 'absent_count',
            'late_count', 'actual_start_time', 'actual_end_time',
            'created_at', 'updated_at'
        ]
    
    def get_group_detail(self, obj):
        return {
            'id': obj.group.id,
            'name': obj.group.name,
            'type': obj.group.group_type,
            'subject': obj.group.subject,
            'max_students': obj.group.max_students
        }
    
    def get_attendance_list(self, obj):
        from attendance.models import Attendance
        from attendance.serializers import AttendanceSerializer
        
        attendance_qs = Attendance.objects.filter(session=obj).select_related('student')
        return AttendanceSerializer(attendance_qs, many=True).data
    
    def get_statistics(self, obj):
        attendance_rate = (obj.present_count / obj.total_students * 100) if obj.total_students > 0 else 0
        
        return {
            'attendance_rate': round(attendance_rate, 2),
            'duration_planned': obj.get_duration_minutes() if hasattr(obj, 'get_duration_minutes') else 0,
            'duration_actual': self._calculate_actual_duration(obj),
            'materials_count': obj.session_materials.count(),
            'notes_count': obj.notes.count()
        }
    
    def _calculate_actual_duration(self, obj):
        if obj.actual_start_time and obj.actual_end_time:
            start_minutes = obj.actual_start_time.hour * 60 + obj.actual_start_time.minute
            end_minutes = obj.actual_end_time.hour * 60 + obj.actual_end_time.minute
            return end_minutes - start_minutes
        return 0


class SessionScheduleSerializer(serializers.Serializer):
    """Serializer for schedule views"""
    date = serializers.DateField()
    sessions = SessionListSerializer(many=True)
    total_sessions = serializers.IntegerField()
    completed_sessions = serializers.IntegerField()
    cancelled_sessions = serializers.IntegerField()