"""
Student Views
"""
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsTeacher, ReadOnlyForStudentsAndParents
from .models import Student, Parent, StudentParentLink, StudentGroup
from .serializers import (
    StudentSerializer, StudentCreateSerializer, StudentListSerializer,
    ParentSerializer, StudentParentLinkSerializer, StudentGroupSerializer,
    StudentProfileSerializer
)


class StudentViewSet(viewsets.ModelViewSet):
    """Student management viewset"""
    permission_classes = [ReadOnlyForStudentsAndParents]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subscription_type', 'subscription_status', 'is_active']
    search_fields = ['name', 'code', 'phone', 'email']
    ordering_fields = ['name', 'registration_date', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        if self.request.user.user_type == 'teacher':
            return Student.objects.filter(teacher=self.request.user)
        elif self.request.user.user_type == 'student':
            return Student.objects.filter(user=self.request.user)
        elif self.request.user.user_type == 'parent':
            # Parents can access their linked students
            linked_student_ids = StudentParentLink.objects.filter(
                parent__user=self.request.user,
                is_active=True
            ).values_list('student_id', flat=True)
            return Student.objects.filter(id__in=linked_student_ids)
        return Student.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StudentCreateSerializer
        elif self.action == 'list':
            return StudentListSerializer
        elif self.action == 'profile':
            return StudentProfileSerializer
        return StudentSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new student"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can create students'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if teacher can add more students
        teacher_profile = getattr(request.user, 'teacher_profile', None)
        if teacher_profile and not teacher_profile.can_add_student():
            return Response(
                {'error': f'Maximum students limit ({teacher_profile.max_students}) reached'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            student = serializer.save()
            response_serializer = StudentSerializer(student)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        """Get detailed student profile"""
        student = self.get_object()
        serializer = StudentProfileSerializer(student)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_remaining_sessions(self, request, pk=None):
        """Update student's remaining sessions"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can update sessions'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        student = self.get_object()
        sessions_to_add = request.data.get('sessions_to_add', 0)
        
        try:
            sessions_to_add = int(sessions_to_add)
            if sessions_to_add <= 0:
                return Response(
                    {'error': 'Sessions to add must be positive'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid sessions value'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        student.remaining_sessions += sessions_to_add
        student.total_sessions_bought += sessions_to_add
        student.save()
        
        return Response({
            'message': f'Added {sessions_to_add} sessions',
            'remaining_sessions': student.remaining_sessions,
            'total_sessions_bought': student.total_sessions_bought
        })
    
    @action(detail=True, methods=['post'])
    def update_subscription(self, request, pk=None):
        """Update student subscription"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can update subscriptions'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        student = self.get_object()
        subscription_type = request.data.get('subscription_type')
        subscription_status = request.data.get('subscription_status')
        
        if subscription_type:
            if subscription_type not in dict(Student.SUBSCRIPTION_TYPES):
                return Response(
                    {'error': 'Invalid subscription type'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            student.subscription_type = subscription_type
        
        if subscription_status:
            if subscription_status not in dict(Student.SUBSCRIPTION_STATUS):
                return Response(
                    {'error': 'Invalid subscription status'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            student.subscription_status = subscription_status
        
        student.save()
        student.update_remaining_amount()
        
        serializer = StudentSerializer(student)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def attendance_history(self, request, pk=None):
        """Get student attendance history"""
        student = self.get_object()
        
        from attendance.models import Attendance
        from attendance.serializers import AttendanceSerializer
        
        attendance_qs = Attendance.objects.filter(
            student=student
        ).select_related('session', 'session__group').order_by('-session__date')
        
        # Apply date filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            attendance_qs = attendance_qs.filter(session__date__gte=start_date)
        if end_date:
            attendance_qs = attendance_qs.filter(session__date__lte=end_date)
        
        # Paginate
        page = self.paginate_queryset(attendance_qs)
        if page is not None:
            serializer = AttendanceSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = AttendanceSerializer(attendance_qs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def payment_history(self, request, pk=None):
        """Get student payment history"""
        student = self.get_object()
        
        from payments.models import Payment
        from payments.serializers import PaymentSerializer
        
        payments_qs = Payment.objects.filter(
            student=student
        ).order_by('-created_at')
        
        # Apply filters
        status_filter = request.query_params.get('status')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if status_filter:
            payments_qs = payments_qs.filter(status=status_filter)
        if start_date:
            payments_qs = payments_qs.filter(payment_date__gte=start_date)
        if end_date:
            payments_qs = payments_qs.filter(payment_date__lte=end_date)
        
        # Paginate
        page = self.paginate_queryset(payments_qs)
        if page is not None:
            serializer = PaymentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PaymentSerializer(payments_qs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def grades_history(self, request, pk=None):
        """Get student grades history"""
        student = self.get_object()
        
        from grades.models import Grade
        from grades.serializers import GradeSerializer
        
        grades_qs = Grade.objects.filter(
            student=student,
            is_active=True
        ).select_related('grade_type', 'session').order_by('-created_at')
        
        # Apply filters
        grade_type = request.query_params.get('grade_type')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if grade_type:
            grades_qs = grades_qs.filter(grade_type__name=grade_type)
        if start_date:
            grades_qs = grades_qs.filter(created_at__gte=start_date)
        if end_date:
            grades_qs = grades_qs.filter(created_at__lte=end_date)
        
        # Paginate
        page = self.paginate_queryset(grades_qs)
        if page is not None:
            serializer = GradeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = GradeSerializer(grades_qs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get student statistics for teacher"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can view statistics'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        
        stats = queryset.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(subscription_status='active')),
            pending=Count('id', filter=Q(subscription_status='pending')),
            suspended=Count('id', filter=Q(subscription_status='suspended')),
            monthly_subscriptions=Count('id', filter=Q(subscription_type='monthly')),
            per_session_subscriptions=Count('id', filter=Q(subscription_type='per_session')),
            free_students=Count('id', filter=Q(subscription_type='free')),
            total_remaining_amount=Sum('remaining_amount')
        )
        
        return Response(stats)


class ParentViewSet(viewsets.ModelViewSet):
    """Parent management viewset"""
    serializer_class = ParentSerializer
    permission_classes = [IsTeacher]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Parent.objects.filter(teacher=self.request.user)
    
    @action(detail=True, methods=['get'])
    def linked_students(self, request, pk=None):
        """Get students linked to this parent"""
        parent = self.get_object()
        links = StudentParentLink.objects.filter(
            parent=parent, 
            is_active=True
        ).select_related('student')
        
        serializer = StudentParentLinkSerializer(links, many=True)
        return Response(serializer.data)


class StudentParentLinkViewSet(viewsets.ModelViewSet):
    """Student-Parent relationship management"""
    serializer_class = StudentParentLinkSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return StudentParentLink.objects.filter(
            student__teacher=self.request.user
        ).select_related('student', 'parent')
    
    def create(self, request, *args, **kwargs):
        """Link student to parent"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            link = serializer.save()
            
            # If this is set as primary contact, remove primary from other links for this student
            if link.is_primary_contact:
                StudentParentLink.objects.filter(
                    student=link.student,
                    is_active=True
                ).exclude(id=link.id).update(is_primary_contact=False)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentGroupViewSet(viewsets.ModelViewSet):
    """Student-Group enrollment management"""
    serializer_class = StudentGroupSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return StudentGroup.objects.filter(
            student__teacher=self.request.user
        ).select_related('student', 'group')
    
    def create(self, request, *args, **kwargs):
        """Enroll student in group"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            student_group = serializer.save()
            
            # Update student remaining amount after enrollment
            student_group.student.update_remaining_amount()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """Remove student from group"""
        instance = self.get_object()
        student = instance.student
        
        # Set as inactive instead of deleting
        instance.is_active = False
        instance.save()
        
        # Update student remaining amount after removal
        student.update_remaining_amount()
        
        return Response(status=status.HTTP_204_NO_CONTENT)