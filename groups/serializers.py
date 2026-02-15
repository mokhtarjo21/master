"""
Group Serializers
"""
from rest_framework import serializers
from django.db import models
from .models import Group, GroupSchedule, GroupMaterial, GroupAnnouncement


class GroupScheduleSerializer(serializers.ModelSerializer):
    """Group schedule serializer"""
    weekday_name = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupSchedule
        fields = [
            'id', 'weekday', 'weekday_name', 'start_time', 'end_time',
            'effective_from', 'effective_until', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_weekday_name(self, obj):
        return dict(GroupSchedule.WEEKDAYS)[obj.weekday]


class GroupMaterialSerializer(serializers.ModelSerializer):
    """Group material serializer"""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupMaterial
        fields = [
            'id', 'title', 'description', 'material_type', 'file',
            'file_url', 'external_link', 'is_public', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class GroupAnnouncementSerializer(serializers.ModelSerializer):
    """Group announcement serializer"""
    is_currently_published = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupAnnouncement
        fields = [
            'id', 'title', 'content', 'is_urgent', 'send_notification',
            'publish_at', 'expire_at', 'is_active', 'is_currently_published',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_is_currently_published(self, obj):
        return obj.is_currently_published()


class GroupSerializer(serializers.ModelSerializer):
    """Main group serializer"""
    current_students = serializers.SerializerMethodField()
    attendance_rate = serializers.SerializerMethodField()
    monthly_revenue = serializers.SerializerMethodField()
    next_session = serializers.SerializerMethodField()
    schedules = GroupScheduleSerializer(many=True, read_only=True)
    
    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'group_type', 'subject', 'grade_level',
            'max_students', 'current_students_count', 'monthly_price',
            'session_price', 'group_discount', 'sessions_per_month',
            'session_duration_minutes', 'classroom', 'online_meeting_link',
            'meeting_password', 'schedule_notes', 'is_active',
            'current_students', 'attendance_rate', 'monthly_revenue',
            'next_session', 'schedules', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'teacher', 'current_students_count', 'created_at', 'updated_at'
        ]
    
    def get_current_students(self, obj):
        students = obj.get_active_students()
        return [
            {
                'id': sg.student.id,
                'name': sg.student.name,
                'code': sg.student.code,
                'enrollment_date': sg.enrollment_date
            }
            for sg in students
        ]
    
    def get_attendance_rate(self, obj):
        # Get attendance rate for current month
        from django.utils import timezone
        current_month = timezone.now().date().replace(day=1)
        return obj.get_attendance_rate(start_date=current_month)
    
    def get_monthly_revenue(self, obj):
        return obj.get_monthly_revenue()
    
    def get_next_session(self, obj):
        next_session = obj.get_next_session()
        if next_session:
            return {
                'id': next_session.id,
                'date': next_session.date,
                'start_time': next_session.start_time,
                'end_time': next_session.end_time
            }
        return None
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return Group.objects.create(**validated_data)


class GroupCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for group creation"""
    
    class Meta:
        model = Group
        fields = [
            'name', 'description', 'group_type', 'subject', 'grade_level',
            'max_students', 'monthly_price', 'session_price', 'group_discount',
            'sessions_per_month', 'session_duration_minutes', 'classroom',
            'online_meeting_link', 'meeting_password', 'schedule_notes'
        ]
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return Group.objects.create(**validated_data)


class GroupListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for group lists"""
    students_count = serializers.IntegerField(source='current_students_count')
    next_session_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = [
            'id', 'name', 'group_type', 'subject', 'max_students',
            'students_count', 'monthly_price', 'session_price',
            'is_active', 'next_session_date'
        ]
    
    def get_next_session_date(self, obj):
        next_session = obj.get_next_session()
        return next_session.date if next_session else None


class GroupDetailSerializer(serializers.ModelSerializer):
    """Detailed group serializer with all related data"""
    students = serializers.SerializerMethodField()
    schedules = GroupScheduleSerializer(many=True, read_only=True)
    materials = GroupMaterialSerializer(many=True, read_only=True)
    announcements = GroupAnnouncementSerializer(many=True, read_only=True)
    statistics = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'group_type', 'subject', 'grade_level',
            'max_students', 'current_students_count', 'monthly_price',
            'session_price', 'group_discount', 'sessions_per_month',
            'session_duration_minutes', 'classroom', 'online_meeting_link',
            'meeting_password', 'schedule_notes', 'is_active',
            'students', 'schedules', 'materials', 'announcements',
            'statistics', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_students_count', 'created_at', 'updated_at']
    
    def get_students(self, obj):
        from students.serializers import StudentListSerializer
        active_enrollments = obj.get_active_students()
        students = [enrollment.student for enrollment in active_enrollments]
        return StudentListSerializer(students, many=True).data
    
    def get_statistics(self, obj):
        from django.utils import timezone
        from django.db.models import Count, Avg
        
        current_month = timezone.now().date().replace(day=1)
        
        # Attendance statistics
        from attendance.models import Attendance
        monthly_attendance = Attendance.objects.filter(
            session__group=obj,
            session__date__gte=current_month
        )
        
        attendance_stats = monthly_attendance.aggregate(
            total=Count('id'),
            present=Count('id', filter=models.Q(status='present')),
            late=Count('id', filter=models.Q(status='late')),
            absent=Count('id', filter=models.Q(status='absent'))
        )
        
        # Session statistics
        from teaching_sessions.models import Session
        monthly_sessions = Session.objects.filter(
            group=obj,
            date__gte=current_month
        )
        
        session_stats = monthly_sessions.aggregate(
            total=Count('id'),
            completed=Count('id', filter=models.Q(status='completed')),
            cancelled=Count('id', filter=models.Q(status='cancelled'))
        )
        
        # Financial statistics
        monthly_revenue = obj.get_monthly_revenue()
        
        return {
            'monthly_attendance': attendance_stats,
            'monthly_sessions': session_stats,
            'monthly_revenue': monthly_revenue,
            'attendance_rate': obj.get_attendance_rate(start_date=current_month)
        }