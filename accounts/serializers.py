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
            print(value)
            student = Student.objects.get(id=value)
            print(student)
            return value
        except Student.DoesNotExist:
            raise serializers.ValidationError('Student not found')


class TeacherRegisterSerializer(serializers.ModelSerializer):
    """Teacher registration using PIN"""
    pin = serializers.CharField(max_length=10, write_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'pin', 'password', 'center_name', 
            'language', 'first_name', 'last_name'
        ]
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value
        
    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value
        
    def create(self, validated_data):
        pin = validated_data.pop('pin')
        # Handle optional password, generate one if not provided since AbstractUser requires it
        password = validated_data.pop('password', None)
        if not password:
            import secrets
            password = secrets.token_urlsafe(16)
            
        validated_data['user_type'] = 'teacher'
        validated_data['is_active'] = True
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        # Set the hashed PIN separately
        user.set_teacher_pin(pin)
        user.save()
        
        # Create profile and notification settings
        from teachers.models import TeacherProfile, TeacherNotificationSettings
        from django.utils import timezone
        from datetime import timedelta
        
        TeacherProfile.objects.create(
            user=user,
            center_name=validated_data.get('center_name', ''),
            email=validated_data.get('email', ''),
            subscription_plan='trial',
            trial_end_date=timezone.now() + timedelta(days=30)
        )
        TeacherNotificationSettings.objects.create(teacher=user)
        
        return user


class GoogleLoginSerializer(serializers.Serializer):
    """Google OAuth login/registration"""
    id_token = serializers.CharField(required=True)
    device_info = serializers.JSONField(required=False, default=dict)