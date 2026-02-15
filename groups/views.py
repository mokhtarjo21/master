"""
Group Views
"""
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import date, timedelta
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsTeacher, ReadOnlyForStudentsAndParents
from .models import Group, GroupSchedule, GroupMaterial, GroupAnnouncement
from .serializers import (
    GroupSerializer, GroupCreateSerializer, GroupListSerializer,
    GroupDetailSerializer, GroupScheduleSerializer, GroupMaterialSerializer,
    GroupAnnouncementSerializer
)


class GroupViewSet(viewsets.ModelViewSet):
    """Group management viewset"""
    permission_classes = [ReadOnlyForStudentsAndParents]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['group_type', 'is_active', 'subject']
    search_fields = ['name', 'description', 'subject']
    ordering_fields = ['name', 'created_at', 'current_students_count']
    ordering = ['name']
    
    def get_queryset(self):
        if self.request.user.user_type == 'teacher':
            return Group.objects.filter(teacher=self.request.user)
        elif self.request.user.user_type in ['student', 'parent']:
            # Students and parents can see groups they're enrolled in
            if self.request.user.user_type == 'student':
                from students.models import StudentGroup
                group_ids = StudentGroup.objects.filter(
                    student__user=self.request.user,
                    is_active=True
                ).values_list('group_id', flat=True)
            else:  # parent
                from students.models import StudentParentLink, StudentGroup
                linked_student_ids = StudentParentLink.objects.filter(
                    parent__user=self.request.user,
                    is_active=True
                ).values_list('student_id', flat=True)
                
                group_ids = StudentGroup.objects.filter(
                    student_id__in=linked_student_ids,
                    is_active=True
                ).values_list('group_id', flat=True)
            
            return Group.objects.filter(id__in=group_ids, is_active=True)
        
        return Group.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return GroupCreateSerializer
        elif self.action == 'list':
            return GroupListSerializer
        elif self.action == 'retrieve':
            return GroupDetailSerializer
        return GroupSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new group"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can create groups'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if teacher can add more groups
        teacher_profile = getattr(request.user, 'teacher_profile', None)
        if teacher_profile and not teacher_profile.can_add_group():
            return Response(
                {'error': f'Maximum groups limit ({teacher_profile.max_groups}) reached'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            group = serializer.save()
            response_serializer = GroupSerializer(group)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Get students in group"""
        group = self.get_object()
        
        from students.models import StudentGroup
        from students.serializers import StudentListSerializer
        
        student_groups = StudentGroup.objects.filter(
            group=group,
            is_active=True
        ).select_related('student')
        
        students = [sg.student for sg in student_groups]
        serializer = StudentListSerializer(students, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_student(self, request, pk=None):
        """Add student to group"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can add students to groups'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        group = self.get_object()
        student_id = request.data.get('student_id')
        
        if not student_id:
            return Response(
                {'error': 'student_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from students.models import Student, StudentGroup
        
        try:
            student = Student.objects.get(
                id=student_id,
                teacher=request.user,
                is_active=True
            )
            
            # Check if group can accept more students
            if not group.can_add_student():
                return Response(
                    {'error': 'Group has reached maximum capacity'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if student is already in group
            if StudentGroup.objects.filter(
                student=student,
                group=group,
                is_active=True
            ).exists():
                return Response(
                    {'error': 'Student is already in this group'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Add student to group
            StudentGroup.objects.create(
                student=student,
                group=group
            )
            
            # Update group student count
            group.save()
            
            return Response({'message': 'Student added to group successfully'})
            
        except Student.DoesNotExist:
            return Response(
                {'error': 'Student not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_student(self, request, pk=None):
        """Remove student from group"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can remove students from groups'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        group = self.get_object()
        student_id = request.data.get('student_id')
        
        if not student_id:
            return Response(
                {'error': 'student_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from students.models import StudentGroup
        
        try:
            student_group = StudentGroup.objects.get(
                student_id=student_id,
                group=group,
                is_active=True
            )
            
            student_group.is_active = False
            student_group.save()
            
            # Update group student count
            group.save()
            
            return Response({'message': 'Student removed from group successfully'})
            
        except StudentGroup.DoesNotExist:
            return Response(
                {'error': 'Student not found in this group'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get group statistics"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can view statistics'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        group = self.get_object()
        
        # Date filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date:
            start_date = timezone.now().date().replace(day=1)  # Current month
        else:
            start_date = date.fromisoformat(start_date)
        
        if not end_date:
            end_date = timezone.now().date()
        else:
            end_date = date.fromisoformat(end_date)
        
        # Session statistics
        from teaching_sessions.models import Session
        sessions = Session.objects.filter(
            group=group,
            date__gte=start_date,
            date__lte=end_date
        )
        
        session_stats = sessions.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled'))
        )
        
        # Attendance statistics
        from attendance.models import Attendance
        attendance = Attendance.objects.filter(
            session__group=group,
            session__date__gte=start_date,
            session__date__lte=end_date
        )
        
        attendance_stats = attendance.aggregate(
            total=Count('id'),
            present=Count('id', filter=Q(status='present')),
            absent=Count('id', filter=Q(status='absent')),
            late=Count('id', filter=Q(status='late'))
        )
        
        # Financial statistics
        revenue = group.get_monthly_revenue()
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'sessions': session_stats,
            'attendance': attendance_stats,
            'revenue': revenue,
            'attendance_rate': group.get_attendance_rate(start_date, end_date)
        })


class GroupScheduleViewSet(viewsets.ModelViewSet):
    """Group schedule management"""
    serializer_class = GroupScheduleSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['group', 'weekday', 'is_active']
    ordering_fields = ['weekday', 'start_time']
    ordering = ['weekday', 'start_time']
    
    def get_queryset(self):
        return GroupSchedule.objects.filter(group__teacher=self.request.user)


class GroupMaterialViewSet(viewsets.ModelViewSet):
    """Group material management"""
    serializer_class = GroupMaterialSerializer
    permission_classes = [ReadOnlyForStudentsAndParents]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['group', 'material_type', 'is_public']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        if self.request.user.user_type == 'teacher':
            return GroupMaterial.objects.filter(group__teacher=self.request.user)
        else:
            # Students and parents can only see public materials for their groups
            if self.request.user.user_type == 'student':
                from students.models import StudentGroup
                group_ids = StudentGroup.objects.filter(
                    student__user=self.request.user,
                    is_active=True
                ).values_list('group_id', flat=True)
            else:  # parent
                from students.models import StudentParentLink, StudentGroup
                linked_student_ids = StudentParentLink.objects.filter(
                    parent__user=self.request.user,
                    is_active=True
                ).values_list('student_id', flat=True)
                
                group_ids = StudentGroup.objects.filter(
                    student_id__in=linked_student_ids,
                    is_active=True
                ).values_list('group_id', flat=True)
            
            return GroupMaterial.objects.filter(
                group_id__in=group_ids,
                is_public=True
            )


class GroupAnnouncementViewSet(viewsets.ModelViewSet):
    """Group announcement management"""
    serializer_class = GroupAnnouncementSerializer
    permission_classes = [ReadOnlyForStudentsAndParents]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['group', 'is_urgent', 'is_active']
    ordering_fields = ['publish_at', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        if self.request.user.user_type == 'teacher':
            return GroupAnnouncement.objects.filter(group__teacher=self.request.user)
        else:
            # Students and parents can see announcements for their groups
            if self.request.user.user_type == 'student':
                from students.models import StudentGroup
                group_ids = StudentGroup.objects.filter(
                    student__user=self.request.user,
                    is_active=True
                ).values_list('group_id', flat=True)
            else:  # parent
                from students.models import StudentParentLink, StudentGroup
                linked_student_ids = StudentParentLink.objects.filter(
                    parent__user=self.request.user,
                    is_active=True
                ).values_list('student_id', flat=True)
                
                group_ids = StudentGroup.objects.filter(
                    student_id__in=linked_student_ids,
                    is_active=True
                ).values_list('group_id', flat=True)
            
            return GroupAnnouncement.objects.filter(
                group_id__in=group_ids,
                is_active=True
            ).filter(
                publish_at__lte=timezone.now()
            )