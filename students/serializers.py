"""
Student Serializers
"""
from rest_framework import serializers
from decimal import Decimal
from .models import Student, Parent, StudentParentLink, StudentGroup


class StudentSerializer(serializers.ModelSerializer):
    """Main student serializer"""
    attendance_rate = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    parents = serializers.SerializerMethodField()
    effective_monthly_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'name', 'code', 'phone', 'whatsapp_number', 'email',
            'date_of_birth', 'address', 'notes', 'subscription_type',
            'subscription_status', 'monthly_price', 'per_session_price',
            'student_discount', 'remaining_sessions', 'total_sessions_bought',
            'total_paid', 'remaining_amount', 'emergency_contact_name',
            'emergency_contact_phone', 'is_active', 'registration_date',
            'attendance_rate', 'groups', 'parents', 'effective_monthly_price',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'code', 'teacher', 'total_paid', 'remaining_amount',
            'registration_date', 'created_at', 'updated_at'
        ]
    
    def get_attendance_rate(self, obj):
        return obj.get_attendance_rate()
    
    def get_groups(self, obj):
        active_groups = obj.student_groups.filter(is_active=True).select_related('group')
        return [
            {
                'id': sg.group.id,
                'name': sg.group.name,
                'type': sg.group.group_type,
                'enrollment_date': sg.enrollment_date
            }
            for sg in active_groups
        ]
    
    def get_parents(self, obj):
        active_links = obj.parent_links.filter(is_active=True).select_related('parent')
        return [
            {
                'id': link.parent.id,
                'name': link.parent.name,
                'phone': link.parent.phone,
                'relationship': link.parent.relationship,
                'is_primary_contact': link.is_primary_contact
            }
            for link in active_links
        ]
    
    def get_effective_monthly_price(self, obj):
        return obj.calculate_discount_price()
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        student = Student.objects.create(**validated_data)
        return student


class StudentCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for student creation"""
    
    class Meta:
        model = Student
        fields = [
            'name', 'phone', 'whatsapp_number', 'email', 'date_of_birth',
            'address', 'notes', 'subscription_type', 'monthly_price',
            'per_session_price', 'student_discount', 'emergency_contact_name',
            'emergency_contact_phone'
        ]
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return Student.objects.create(**validated_data)


class StudentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for student lists"""
    groups_count = serializers.SerializerMethodField()
    last_attendance = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'name', 'code', 'phone', 'subscription_type',
            'subscription_status', 'remaining_sessions', 'remaining_amount',
            'groups_count', 'last_attendance', 'payment_status', 'is_active'
        ]
    
    def get_groups_count(self, obj):
        return obj.student_groups.filter(is_active=True).count()
    
    def get_last_attendance(self, obj):
        from attendance.models import Attendance
        last_attendance = Attendance.objects.filter(student=obj).order_by('-session__date').first()
        if last_attendance:
            return {
                'date': last_attendance.session.date,
                'status': last_attendance.status
            }
        return None
    
    def get_payment_status(self, obj):
        if obj.subscription_type == 'free':
            return 'free'
        elif obj.remaining_amount > 0:
            return 'pending'
        else:
            return 'paid'


class ParentSerializer(serializers.ModelSerializer):
    """Parent serializer"""
    linked_students = serializers.SerializerMethodField()
    
    class Meta:
        model = Parent
        fields = [
            'id', 'name', 'phone', 'whatsapp_number', 'email',
            'relationship', 'is_active', 'linked_students',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at']
    
    def get_linked_students(self, obj):
        active_links = obj.student_links.filter(is_active=True).select_related('student')
        return [
            {
                'id': link.student.id,
                'name': link.student.name,
                'code': link.student.code,
                'is_primary_contact': link.is_primary_contact
            }
            for link in active_links
        ]
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return Parent.objects.create(**validated_data)


class StudentParentLinkSerializer(serializers.ModelSerializer):
    """Student-Parent relationship serializer"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = StudentParentLink
        fields = [
            'id', 'student', 'parent', 'student_name', 'parent_name',
            'is_primary_contact', 'can_receive_notifications',
            'can_view_grades', 'can_view_attendance', 'can_view_payments',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        student = data['student']
        parent = data['parent']
        
        # Ensure both belong to same teacher
        if student.teacher != parent.teacher:
            raise serializers.ValidationError("Student and parent must belong to the same teacher")
        
        # Ensure teacher owns both
        request = self.context.get('request')
        if request and request.user != student.teacher:
            raise serializers.ValidationError("You can only link your own students and parents")
        
        return data


class StudentGroupSerializer(serializers.ModelSerializer):
    """Student-Group relationship serializer"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    effective_monthly_price = serializers.SerializerMethodField()
    effective_session_price = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentGroup
        fields = [
            'id', 'student', 'group', 'student_name', 'group_name',
            'enrollment_date', 'is_active', 'custom_monthly_price',
            'custom_session_price', 'effective_monthly_price',
            'effective_session_price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'enrollment_date', 'created_at', 'updated_at']
    
    def get_effective_monthly_price(self, obj):
        return obj.get_effective_monthly_price()
    
    def get_effective_session_price(self, obj):
        return obj.get_effective_session_price()
    
    def validate(self, data):
        student = data['student']
        group = data['group']
        
        # Ensure both belong to same teacher
        if student.teacher != group.teacher:
            raise serializers.ValidationError("Student and group must belong to the same teacher")
        
        # Ensure teacher owns both
        request = self.context.get('request')
        if request and request.user != student.teacher:
            raise serializers.ValidationError("You can only enroll your own students in your groups")
        
        # Check if student is already in group
        if StudentGroup.objects.filter(student=student, group=group, is_active=True).exists():
            raise serializers.ValidationError("Student is already enrolled in this group")
        
        return data


class StudentProfileSerializer(serializers.ModelSerializer):
    """Complete student profile for detailed view"""
    attendance_summary = serializers.SerializerMethodField()
    payment_summary = serializers.SerializerMethodField()
    grades_summary = serializers.SerializerMethodField()
    groups_detail = serializers.SerializerMethodField()
    parents_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'name', 'code', 'phone', 'whatsapp_number', 'email',
            'date_of_birth', 'address', 'notes', 'subscription_type',
            'subscription_status', 'monthly_price', 'per_session_price',
            'student_discount', 'remaining_sessions', 'total_sessions_bought',
            'total_paid', 'remaining_amount', 'emergency_contact_name',
            'emergency_contact_phone', 'registration_date', 'is_active',
            'attendance_summary', 'payment_summary', 'grades_summary',
            'groups_detail', 'parents_detail', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'code', 'total_paid', 'remaining_amount', 'registration_date',
            'created_at', 'updated_at'
        ]
    
    def get_attendance_summary(self, obj):
        from attendance.models import Attendance
        from django.db.models import Count
        from django.utils import timezone
        
        # Current month attendance
        from django.db import models
        current_month = timezone.now().date().replace(day=1)
        monthly_attendance = Attendance.objects.filter(
            student=obj,
            session__date__gte=current_month
        ).aggregate(
            total=Count('id'),
            present=Count('id', filter=models.Q(status='present')),
            absent=Count('id', filter=models.Q(status='absent')),
            late=Count('id', filter=models.Q(status='late'))
        )
        
        return {
            'monthly_total': monthly_attendance['total'],
            'monthly_present': monthly_attendance['present'],
            'monthly_absent': monthly_attendance['absent'],
            'monthly_late': monthly_attendance['late'],
            'monthly_rate': obj.get_attendance_rate(start_date=current_month),
            'overall_rate': obj.get_attendance_rate()
        }
    
    def get_payment_summary(self, obj):
        from payments.models import Payment
        from django.db.models import Sum, Count
        from django.utils import timezone
        
        current_month = timezone.now().date().replace(day=1)
        
        payments = Payment.objects.filter(student=obj)
        monthly_payments = payments.filter(payment_date__gte=current_month)
        
        return {
            'total_paid': obj.total_paid,
            'remaining_amount': obj.remaining_amount,
            'monthly_payments': monthly_payments.aggregate(
                total=Sum('amount'),
                count=Count('id')
            ),
            'pending_payments': payments.filter(status='pending').aggregate(
                total=Sum('amount'),
                count=Count('id')
            ),
            'overdue_payments': payments.filter(status='overdue').aggregate(
                total=Sum('amount'),
                count=Count('id')
            )
        }
    
    def get_grades_summary(self, obj):
        from grades.models import Grade
        from django.db.models import Avg, Count
        
        grades = Grade.objects.filter(student=obj, is_active=True)
        
        if not grades.exists():
            return None
        
        return {
            'total_grades': grades.count(),
            'average_grade': grades.aggregate(avg=Avg('grade'))['avg'],
            'grade_types': list(grades.values_list('grade_type__name', flat=True).distinct())
        }
    
    def get_groups_detail(self, obj):
        return StudentGroupSerializer(
            obj.student_groups.filter(is_active=True),
            many=True
        ).data
    
    def get_parents_detail(self, obj):
        return StudentParentLinkSerializer(
            obj.parent_links.filter(is_active=True),
            many=True
        ).data