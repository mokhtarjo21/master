"""
Attendance Views
"""
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import date, timedelta
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsTeacher, ReadOnlyForStudentsAndParents
from .models import Attendance, AttendanceQRCode, AttendanceSummary, AttendanceAlert
from .serializers import (
    AttendanceSerializer, AttendanceCreateSerializer, BulkAttendanceSerializer,
    AttendanceQRCodeSerializer, AttendanceSummarySerializer, AttendanceAlertSerializer,
    AttendanceReportSerializer, QRAttendanceSerializer
)


class AttendanceViewSet(viewsets.ModelViewSet):
    """Attendance management viewset"""
    permission_classes = [ReadOnlyForStudentsAndParents]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'method', 'session__group']
    search_fields = ['student__name', 'student__code', 'session__title']
    ordering_fields = ['marked_at', 'session__date']
    ordering = ['-marked_at']
    
    def get_queryset(self):
        if self.request.user.user_type == 'teacher':
            return Attendance.objects.filter(
                session__group__teacher=self.request.user
            ).select_related('student', 'session', 'session__group')
        elif self.request.user.user_type == 'student':
            return Attendance.objects.filter(
                student__user=self.request.user
            ).select_related('session', 'session__group')
        elif self.request.user.user_type == 'parent':
            from students.models import StudentParentLink
            linked_student_ids = StudentParentLink.objects.filter(
                parent__user=self.request.user,
                is_active=True,
                can_view_attendance=True
            ).values_list('student_id', flat=True)
            
            return Attendance.objects.filter(
                student_id__in=linked_student_ids
            ).select_related('student', 'session', 'session__group')
        
        return Attendance.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AttendanceCreateSerializer
        return AttendanceSerializer
    
    def create(self, request, *args, **kwargs):
        """Create attendance record"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can mark attendance'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            attendance = serializer.save(marked_by=request.user)
            response_serializer = AttendanceSerializer(attendance)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create attendance records"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can mark attendance'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BulkAttendanceSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            session_id = serializer.validated_data['session_id']
            attendance_records = serializer.validated_data['attendance_records']
            
            from teaching_sessions.models import Session
            session = Session.objects.get(id=session_id)
            
            created_count = 0
            updated_count = 0
            errors = []
            
            for record in attendance_records:
                try:
                    student_id = record['student_id']
                    status_value = record['status']
                    notes = record.get('notes', '')
                    excuse_reason = record.get('excuse_reason', '')
                    
                    attendance, created = Attendance.objects.update_or_create(
                        session=session,
                        student_id=student_id,
                        defaults={
                            'status': status_value,
                            'notes': notes,
                            'excuse_reason': excuse_reason,
                            'method': 'bulk',
                            'marked_by': request.user,
                            'marked_at': timezone.now()
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        
                except Exception as e:
                    errors.append(f"Error processing student {student_id}: {str(e)}")
            
            # Update session attendance summary
            session.update_attendance_summary()
            
            return Response({
                'message': f'Bulk attendance completed: {created_count} created, {updated_count} updated',
                'created': created_count,
                'updated': updated_count,
                'errors': errors
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def session_attendance(self, request):
        """Get attendance for a specific session"""
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response(
                {'error': 'session_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(session_id=session_id)
        serializer = AttendanceSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def student_attendance(self, request):
        """Get attendance for a specific student"""
        student_id = request.query_params.get('student_id')
        if not student_id:
            return Response(
                {'error': 'student_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(student_id=student_id)
        
        # Apply date filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(session__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(session__date__lte=end_date)
        
        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AttendanceSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = AttendanceSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get attendance statistics"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can view statistics'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        
        # Apply filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        group_id = request.query_params.get('group_id')
        
        if start_date:
            queryset = queryset.filter(session__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(session__date__lte=end_date)
        if group_id:
            queryset = queryset.filter(session__group_id=group_id)
        
        stats = queryset.aggregate(
            total=Count('id'),
            present=Count('id', filter=Q(status='present')),
            absent=Count('id', filter=Q(status='absent')),
            late=Count('id', filter=Q(status='late')),
            excused=Count('id', filter=Q(status='excused'))
        )
        
        # Calculate rates
        if stats['total'] > 0:
            stats['attendance_rate'] = round(
                ((stats['present'] + stats['late'] + stats['excused']) / stats['total']) * 100, 2
            )
            stats['punctuality_rate'] = round(
                (stats['present'] / (stats['present'] + stats['late'])) * 100, 2
            ) if (stats['present'] + stats['late']) > 0 else 0
        else:
            stats['attendance_rate'] = 0
            stats['punctuality_rate'] = 0
        
        return Response(stats)
    
    @action(detail=False, methods=['post'])
    def generate_qr(self, request):
        """Generate QR code for session attendance"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can generate QR codes'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        session_id = request.data.get('session_id')
        if not session_id:
            return Response(
                {'error': 'session_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from teaching_sessions.models import Session
        try:
            session = Session.objects.get(id=session_id, group__teacher=request.user)
        except Session.DoesNotExist:
            return Response(
                {'error': 'Session not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create QR code
        import secrets
        import json
        
        qr_token = secrets.token_urlsafe(32)
        qr_data = json.dumps({
            'session_id': str(session.id),
            'session_title': session.title,
            'date': session.date.isoformat(),
            'time': session.start_time.strftime('%H:%M')
        })
        
        # Set validity period (default 2 hours)
        valid_until = timezone.now() + timedelta(hours=2)
        
        qr_code = AttendanceQRCode.objects.create(
            session=session,
            qr_token=qr_token,
            qr_data=qr_data,
            valid_until=valid_until,
            created_by=request.user
        )
        
        serializer = AttendanceQRCodeSerializer(qr_code, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def qr_scan_attendance(request, qr_token):
    """Mark attendance via QR code scan"""
    serializer = QRAttendanceSerializer(data={
        'qr_token': qr_token,
        'student_code': request.data.get('student_code', '')
    })
    
    if serializer.is_valid():
        qr_token = serializer.validated_data['qr_token']
        student_code = serializer.validated_data['student_code']
        
        try:
            # Get QR code and session
            qr_code = AttendanceQRCode.objects.get(qr_token=qr_token)
            session = qr_code.session
            
            # Get student
            from students.models import Student
            student = Student.objects.get(code=student_code, is_active=True)
            
            # Check if student is enrolled in the session's group
            from students.models import StudentGroup
            if not StudentGroup.objects.filter(
                student=student,
                group=session.group,
                is_active=True
            ).exists():
                return Response(
                    {'error': 'Student is not enrolled in this session'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Mark attendance
            attendance, created = Attendance.objects.update_or_create(
                session=session,
                student=student,
                defaults={
                    'status': 'present',
                    'method': 'qr_code',
                    'qr_token': qr_token,
                    'marked_at': timezone.now()
                }
            )
            
            # Increment QR scan count
            qr_code.increment_scan_count()
            
            # Update session attendance summary
            session.update_attendance_summary()
            
            return Response({
                'message': 'Attendance marked successfully',
                'student_name': student.name,
                'session_title': session.title,
                'status': attendance.status,
                'marked_at': attendance.marked_at
            })
            
        except AttendanceQRCode.DoesNotExist:
            return Response(
                {'error': 'Invalid QR code'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Student.DoesNotExist:
            return Response(
                {'error': 'Invalid student code'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error marking attendance: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AttendanceSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """Attendance summary viewset"""
    serializer_class = AttendanceSummarySerializer
    permission_classes = [ReadOnlyForStudentsAndParents]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['summary_type', 'student']
    ordering_fields = ['period_start', 'attendance_rate']
    ordering = ['-period_start']
    
    def get_queryset(self):
        if self.request.user.user_type == 'teacher':
            return AttendanceSummary.objects.filter(
                student__teacher=self.request.user
            ).select_related('student')
        elif self.request.user.user_type == 'student':
            return AttendanceSummary.objects.filter(
                student__user=self.request.user
            )
        elif self.request.user.user_type == 'parent':
            from students.models import StudentParentLink
            linked_student_ids = StudentParentLink.objects.filter(
                parent__user=self.request.user,
                is_active=True,
                can_view_attendance=True
            ).values_list('student_id', flat=True)
            
            return AttendanceSummary.objects.filter(
                student_id__in=linked_student_ids
            ).select_related('student')
        
        return AttendanceSummary.objects.none()


class AttendanceAlertViewSet(viewsets.ModelViewSet):
    """Attendance alert viewset"""
    serializer_class = AttendanceAlertSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['alert_type', 'severity', 'is_active', 'is_resolved']
    ordering_fields = ['created_at', 'severity']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return AttendanceAlert.objects.filter(
            student__teacher=self.request.user
        ).select_related('student')
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an attendance alert"""
        alert = self.get_object()
        alert.resolve(resolved_by=request.user)
        
        serializer = AttendanceAlertSerializer(alert)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_resolve(self, request):
        """Bulk resolve attendance alerts"""
        alert_ids = request.data.get('alert_ids', [])
        
        if not alert_ids:
            return Response(
                {'error': 'alert_ids is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        alerts = self.get_queryset().filter(id__in=alert_ids, is_active=True)
        resolved_count = 0
        
        for alert in alerts:
            alert.resolve(resolved_by=request.user)
            resolved_count += 1
        
        return Response({
            'message': f'Resolved {resolved_count} alerts',
            'resolved_count': resolved_count
        })