"""
Parent-specific Views
Read-only access for parents to view their linked students' data
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from accounts.permissions import IsParent, ReadOnlyForStudentsAndParents
from students.models import StudentParentLink, Student
from students.serializers import StudentSerializer, StudentProfileSerializer


class ParentDashboardViewSet(viewsets.ViewSet):
    """Parent dashboard with read-only access to linked students"""
    permission_classes = [IsParent]
    
    def list(self, request):
        """Get parent dashboard with linked students summary"""
        parent_profile = getattr(request.user, 'parent_profile', None)
        if not parent_profile:
            return Response(
                {'error': 'Parent profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get linked students
        linked_students = StudentParentLink.objects.filter(
            parent=parent_profile,
            is_active=True
        ).select_related('student').values_list('student', flat=True)
        
        students = Student.objects.filter(
            id__in=linked_students,
            is_active=True
        )
        
        students_data = []
        for student in students:
            # Get quick summary for each student
            from attendance.models import Attendance
            from payments.models import Payment
            from django.utils import timezone
            
            current_month = timezone.now().date().replace(day=1)
            
            # Monthly attendance
            monthly_attendance = Attendance.objects.filter(
                student=student,
                session__date__gte=current_month
            )
            attendance_rate = 0
            if monthly_attendance.exists():
                present_count = monthly_attendance.filter(status__in=['present', 'late']).count()
                attendance_rate = (present_count / monthly_attendance.count()) * 100
            
            # Payment status
            pending_payments = Payment.objects.filter(
                student=student,
                status='pending'
            ).count()
            
            # Recent grades
            from grades.models import Grade
            recent_grades = Grade.objects.filter(
                student=student,
                is_active=True
            ).order_by('-created_at')[:3]
            
            students_data.append({
                'id': student.id,
                'name': student.name,
                'code': student.code,
                'subscription_type': student.subscription_type,
                'subscription_status': student.subscription_status,
                'remaining_sessions': student.remaining_sessions,
                'remaining_amount': student.remaining_amount,
                'monthly_attendance_rate': round(attendance_rate, 2),
                'pending_payments_count': pending_payments,
                'recent_grades': [
                    {
                        'grade_type': grade.grade_type.name if grade.grade_type else 'N/A',
                        'grade': grade.grade,
                        'created_at': grade.created_at
                    }
                    for grade in recent_grades
                ]
            })
        
        return Response({
            'parent_name': parent_profile.name,
            'linked_students_count': len(students_data),
            'students': students_data
        })
    
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)')
    def student_detail(self, request, student_id=None):
        """Get detailed information for a specific linked student"""
        parent_profile = getattr(request.user, 'parent_profile', None)
        if not parent_profile:
            return Response(
                {'error': 'Parent profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if parent has access to this student
        try:
            link = StudentParentLink.objects.get(
                parent=parent_profile,
                student_id=student_id,
                is_active=True
            )
            student = link.student
        except StudentParentLink.DoesNotExist:
            return Response(
                {'error': 'Student not found or access denied'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions
        permissions = {
            'can_view_grades': link.can_view_grades,
            'can_view_attendance': link.can_view_attendance,
            'can_view_payments': link.can_view_payments,
        }
        
        serializer = StudentProfileSerializer(student)
        data = serializer.data
        
        # Filter data based on permissions
        if not permissions['can_view_grades']:
            data.pop('grades_summary', None)
        if not permissions['can_view_attendance']:
            data.pop('attendance_summary', None)
        if not permissions['can_view_payments']:
            data.pop('payment_summary', None)
        
        data['permissions'] = permissions
        
        return Response(data)
    
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)/attendance')
    def student_attendance(self, request, student_id=None):
        """Get attendance history for linked student"""
        parent_profile = getattr(request.user, 'parent_profile', None)
        if not parent_profile:
            return Response(
                {'error': 'Parent profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check access and permissions
        try:
            link = StudentParentLink.objects.get(
                parent=parent_profile,
                student_id=student_id,
                is_active=True,
                can_view_attendance=True
            )
            student = link.student
        except StudentParentLink.DoesNotExist:
            return Response(
                {'error': 'Student not found or access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        from attendance.models import Attendance
        from attendance.serializers import AttendanceSerializer
        
        # Get attendance with filters
        attendance_qs = Attendance.objects.filter(
            student=student
        ).select_related('session', 'session__group').order_by('-session__date')
        
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
    
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)/payments')
    def student_payments(self, request, student_id=None):
        """Get payment history for linked student"""
        parent_profile = getattr(request.user, 'parent_profile', None)
        if not parent_profile:
            return Response(
                {'error': 'Parent profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check access and permissions
        try:
            link = StudentParentLink.objects.get(
                parent=parent_profile,
                student_id=student_id,
                is_active=True,
                can_view_payments=True
            )
            student = link.student
        except StudentParentLink.DoesNotExist:
            return Response(
                {'error': 'Student not found or access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        from payments.models import Payment
        from payments.serializers import PaymentSerializer
        
        # Get payments with filters
        payments_qs = Payment.objects.filter(
            student=student
        ).order_by('-created_at')
        
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
    
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)/grades')
    def student_grades(self, request, student_id=None):
        """Get grades history for linked student"""
        parent_profile = getattr(request.user, 'parent_profile', None)
        if not parent_profile:
            return Response(
                {'error': 'Parent profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check access and permissions
        try:
            link = StudentParentLink.objects.get(
                parent=parent_profile,
                student_id=student_id,
                is_active=True,
                can_view_grades=True
            )
            student = link.student
        except StudentParentLink.DoesNotExist:
            return Response(
                {'error': 'Student not found or access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        from grades.models import Grade
        from grades.serializers import GradeSerializer
        
        # Get grades with filters
        grades_qs = Grade.objects.filter(
            student=student,
            is_active=True
        ).select_related('grade_type', 'session').order_by('-created_at')
        
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
    
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)/reports')
    def student_reports(self, request, student_id=None):
        """Get available reports for linked student"""
        parent_profile = getattr(request.user, 'parent_profile', None)
        if not parent_profile:
            return Response(
                {'error': 'Parent profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check access
        try:
            link = StudentParentLink.objects.get(
                parent=parent_profile,
                student_id=student_id,
                is_active=True
            )
            student = link.student
        except StudentParentLink.DoesNotExist:
            return Response(
                {'error': 'Student not found or access denied'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get available reports based on permissions
        available_reports = []
        
        if link.can_view_attendance:
            available_reports.append({
                'type': 'attendance',
                'title': 'Attendance Report',
                'description': 'Student attendance history and statistics',
                'endpoint': f'/api/parents/student/{student_id}/attendance/'
            })
        
        if link.can_view_payments:
            available_reports.append({
                'type': 'payments',
                'title': 'Payment Report',
                'description': 'Student payment history and financial status',
                'endpoint': f'/api/parents/student/{student_id}/payments/'
            })
        
        if link.can_view_grades:
            available_reports.append({
                'type': 'grades',
                'title': 'Grades Report',
                'description': 'Student grades and academic performance',
                'endpoint': f'/api/parents/student/{student_id}/grades/'
            })
        
        return Response({
            'student_name': student.name,
            'student_code': student.code,
            'available_reports': available_reports
        })