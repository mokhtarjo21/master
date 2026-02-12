"""
Authentication Serializers
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, TeacherSession
import uuid


class TeacherLoginSerializer(serializers.Serializer):
    """Teacher PIN-based login"""
    pin = serializers.CharField(max_length=10)
    device_info = serializers.JSONField(required=False, default=dict)
    
    def validate(self, attrs):
        pin = attrs.get('pin')
        
        # Find teacher by PIN
        teachers = User.objects.filter(user_type='teacher', teacher_pin__isnull=False)
        teacher = None
        
        for t in teachers:
            if t.check_teacher_pin(pin):
                teacher = t
                break
        
        if not teacher:
            raise serializers.ValidationError('Invalid PIN')
        
        if not teacher.is_active:
            raise serializers.ValidationError('Teacher account is disabled')
        
        attrs['teacher'] = teacher
        return attrs


class StudentLoginSerializer(serializers.Serializer):
    """Student/Parent login via code, token, or QR"""
    student_code = serializers.CharField(max_length=20, required=False)
    access_token = serializers.CharField(max_length=255, required=False)
    qr_token = serializers.CharField(max_length=255, required=False)
    
    def validate(self, attrs):
        student_code = attrs.get('student_code')
        access_token = attrs.get('access_token')
        qr_token = attrs.get('qr_token')
        
        user = None
        
        if student_code:
            try:
                user = User.objects.get(
                    student_code=student_code,
                    user_type__in=['student', 'parent'],
                    is_active=True
                )
            except User.DoesNotExist:
                raise serializers.ValidationError('Invalid student code')
        
        elif access_token:
            try:
                user = User.objects.get(
                    access_token=access_token,
                    user_type__in=['student', 'parent'],
                    is_active=True
                )
            except User.DoesNotExist:
                raise serializers.ValidationError('Invalid access token')
        
        elif qr_token:
            try:
                user = User.objects.get(
                    qr_token=qr_token,
                    user_type__in=['student', 'parent'],
                    is_active=True
                )
                if not user.is_qr_token_valid():
                    raise serializers.ValidationError('QR code expired')
            except User.DoesNotExist:
                raise serializers.ValidationError('Invalid QR token')
        
        else:
            raise serializers.ValidationError('Must provide student_code, access_token, or qr_token')
        
        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """User profile serializer"""
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'user_type', 'language',
            'center_name', 'student_code', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'student_code', 'created_at']


class TeacherProfileSerializer(serializers.ModelSerializer):
    """Teacher profile with additional fields"""
    active_students_count = serializers.SerializerMethodField()
    active_groups_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'center_name', 'language',
            'active_students_count', 'active_groups_count', 'last_activity'
        ]
        read_only_fields = ['id', 'last_activity']
    
    def get_active_students_count(self, obj):
        from students.models import Student
        return Student.objects.filter(teacher=obj, is_active=True).count()
    
    def get_active_groups_count(self, obj):
        from groups.models import Group
        return Group.objects.filter(teacher=obj, is_active=True).count()


class StudentQRSerializer(serializers.Serializer):
    """Generate QR code for student access"""
    student_id = serializers.UUIDField()
    
    def validate_student_id(self, value):
        from students.models import Student
        try:
            student = Student.objects.get(id=value, is_active=True)
            return value
        except Student.DoesNotExist:
            raise serializers.ValidationError('Student not found')