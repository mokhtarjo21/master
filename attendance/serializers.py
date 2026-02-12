"""
Attendance Serializers
"""
from rest_framework import serializers
from .models import Attendance, AttendanceQRCode, AttendanceSummary, AttendanceAlert


class AttendanceSerializer(serializers.ModelSerializer):
    """Main attendance serializer"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_code = serializers.CharField(source='student.code', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    session_date = serializers.DateField(source='session.date', read_only=True)
    session_time = serializers.TimeField(source='session.start_time', read_only=True)
    is_late = serializers.SerializerMethodField()
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'session', 'student', 'student_name', 'student_code',
            'session_title', 'session_date', 'session_time', 'status',
            'method', 'marked_at', 'arrival_time', 'notes', 'excuse_reason',
            'is_late', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'marked_at', 'created_at', 'updated_at']
    
    def get_is_late(self, obj):
        return obj.is_late()


class AttendanceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating attendance records"""
    
    class Meta:
        model = Attendance
        fields = [
            'session', 'student', 'status', 'method', 'arrival_time',
            'notes', 'excuse_reason'
        ]
    
    def validate(self, data):
        session = data.get('session')
        student = data.get('student')
        
        # Ensure student is enrolled in the session's group
        from students.models import StudentGroup
        if not StudentGroup.objects.filter(
            student=student,
            group=session.group,
            is_active=True
        ).exists():
            raise serializers.ValidationError("Student is not enrolled in this session's group")
        
        # Ensure teacher owns the session
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if session.group.teacher != request.user:
                raise serializers.ValidationError("You can only mark attendance for your own sessions")
        
        return data


class BulkAttendanceSerializer(serializers.Serializer):
    """Serializer for bulk attendance operations"""
    session_id = serializers.UUIDField()
    attendance_records = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        )
    )
    
    def validate_session_id(self, value):
        from sessions.models import Session
        try:
            session = Session.objects.get(id=value)
            # Ensure teacher owns the session
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                if session.group.teacher != request.user:
                    raise serializers.ValidationError("You can only mark attendance for your own sessions")
            return value
        except Session.DoesNotExist:
            raise serializers.ValidationError("Session not found")
    
    def validate_attendance_records(self, value):
        for record in value:
            if 'student_id' not in record or 'status' not in record:
                raise serializers.ValidationError("Each record must have student_id and status")
            
            if record['status'] not in dict(Attendance.ATTENDANCE_STATUS):
                raise serializers.ValidationError(f"Invalid status: {record['status']}")
        
        return value


class AttendanceQRCodeSerializer(serializers.ModelSerializer):
    """QR code serializer"""
    is_valid = serializers.SerializerMethodField()
    qr_url = serializers.SerializerMethodField()
    
    class Meta:
        model = AttendanceQRCode
        fields = [
            'id', 'session', 'qr_token', 'qr_data', 'valid_from',
            'valid_until', 'is_active', 'scan_count', 'max_scans',
            'is_valid', 'qr_url', 'created_at'
        ]
        read_only_fields = ['id', 'qr_token', 'scan_count', 'created_at']
    
    def get_is_valid(self, obj):
        return obj.is_valid()
    
    def get_qr_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/attendance/qr-scan/{obj.qr_token}/')
        return None


class AttendanceSummarySerializer(serializers.ModelSerializer):
    """Attendance summary serializer"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    
    class Meta:
        model = AttendanceSummary
        fields = [
            'id', 'student', 'student_name', 'summary_type',
            'period_start', 'period_end', 'total_sessions',
            'present_count', 'absent_count', 'late_count',
            'excused_count', 'attendance_rate', 'punctuality_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'attendance_rate', 'punctuality_rate',
            'created_at', 'updated_at'
        ]


class AttendanceAlertSerializer(serializers.ModelSerializer):
    """Attendance alert serializer"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_code = serializers.CharField(source='student.code', read_only=True)
    
    class Meta:
        model = AttendanceAlert
        fields = [
            'id', 'student', 'student_name', 'student_code',
            'alert_type', 'severity', 'title', 'message',
            'trigger_data', 'is_active', 'is_resolved',
            'resolved_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'trigger_data', 'resolved_at', 'created_at'
        ]


class AttendanceReportSerializer(serializers.Serializer):
    """Serializer for attendance reports"""
    student_id = serializers.UUIDField(required=False)
    group_id = serializers.UUIDField(required=False)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    include_summary = serializers.BooleanField(default=True)
    include_details = serializers.BooleanField(default=True)
    
    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start date must be before end date")
        return data


class QRAttendanceSerializer(serializers.Serializer):
    """Serializer for QR code attendance marking"""
    qr_token = serializers.CharField()
    student_code = serializers.CharField()
    
    def validate_qr_token(self, value):
        try:
            qr_code = AttendanceQRCode.objects.get(qr_token=value)
            if not qr_code.is_valid():
                raise serializers.ValidationError("QR code is expired or invalid")
            return value
        except AttendanceQRCode.DoesNotExist:
            raise serializers.ValidationError("Invalid QR code")
    
    def validate_student_code(self, value):
        from students.models import Student
        try:
            student = Student.objects.get(code=value, is_active=True)
            return value
        except Student.DoesNotExist:
            raise serializers.ValidationError("Invalid student code")