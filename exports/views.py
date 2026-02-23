"""
Exports Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.http import FileResponse
from datetime import timedelta
from accounts.permissions import IsTeacher
from .models import Export
from .serializers import ExportSerializer, ExportRequestSerializer


class ExportViewSet(viewsets.ModelViewSet):
    """Export management viewset"""
    serializer_class = ExportSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return Export.objects.filter(teacher=self.request.user)
    
    @action(detail=False, methods=['post'])
    def students(self, request):
        """Export students data"""
        from students.models import Student
        from .utils import generate_students_csv, save_export_file
        
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        export = Export.objects.create(
            teacher=request.user,
            export_type='students',
            format=serializer.validated_data.get('format', 'csv'),
            filters=serializer.validated_data.get('filters', {}),
            fields=serializer.validated_data.get('fields', []),
            status='processing',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        try:
            # Get students data
            students = Student.objects.filter(teacher=request.user)
            
            # Apply filters if provided
            filters = export.filters
            if filters:
                if 'subscription_type' in filters:
                    students = students.filter(subscription_type=filters['subscription_type'])
                if 'created_at__gte' in filters:
                    students = students.filter(created_at__gte=filters['created_at__gte'])
            
            # Generate CSV
            if export.format == 'csv':
                content = generate_students_csv(students, export.fields or None)
                filename = f'students_{export.id}.csv'
            else:
                raise ValueError(f"Format {export.format} not yet supported")
            
            # Save file
            export.records_count = students.count()
            save_export_file(export, content, filename)
            
            return Response({
                'export_id': export.id,
                'status': 'completed',
                'download_url': export.file.url if export.file else None,
                'records_count': export.records_count,
                'file_size': export.file_size
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            export.status = 'failed'
            export.error_message = str(e)
            export.save()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def payments(self, request):
        """Export payments data"""
        from payments.models import Payment
        from .utils import generate_payments_csv, save_export_file
        
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        export = Export.objects.create(
            teacher=request.user,
            export_type='payments',
            format=serializer.validated_data.get('format', 'csv'),
            filters=serializer.validated_data.get('filters', {}),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        try:
            # Get payments data
            payments = Payment.objects.filter(student__teacher=request.user)
            
            # Apply date filters
            filters = export.filters
            if filters:
                if 'start_date' in filters:
                    payments = payments.filter(created_at__date__gte=filters['start_date'])
                if 'end_date' in filters:
                    payments = payments.filter(created_at__date__lte=filters['end_date'])
                if 'status' in filters:
                    payments = payments.filter(status=filters['status'])
            
            # Generate CSV
            content = generate_payments_csv(payments, export.fields or None)
            filename = f'payments_{export.id}.csv'
            
            # Save file
            export.records_count = payments.count()
            save_export_file(export, content, filename)
            
            return Response({
                'export_id': export.id,
                'status': 'completed',
                'download_url': export.file.url,
                'records_count': export.records_count
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            export.status = 'failed'
            export.error_message = str(e)
            export.save()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def attendance(self, request):
        """Export attendance data"""
        from attendance.models import Attendance
        from .utils import generate_attendance_csv, save_export_file
        
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        export = Export.objects.create(
            teacher=request.user,
            export_type='attendance',
            format=serializer.validated_data.get('format', 'csv'),
            filters=serializer.validated_data.get('filters', {}),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        try:
            # Get attendance records
            attendance = Attendance.objects.filter(student__teacher=request.user)
            
            # Apply filters
            filters = export.filters
            if filters:
                if 'start_date' in filters:
                    attendance = attendance.filter(date__gte=filters['start_date'])
                if 'end_date' in filters:
                    attendance = attendance.filter(date__lte=filters['end_date'])
                if 'status' in filters:
                    attendance = attendance.filter(status=filters['status'])
            
            # Generate CSV
            content = generate_attendance_csv(attendance, export.fields or None)
            filename = f'attendance_{export.id}.csv'
            
            # Save file
            export.records_count = attendance.count()
            save_export_file(export, content, filename)
            
            return Response({
                'export_id': export.id,
                'status': 'completed',
                'download_url': export.file.url,
                'records_count': export.records_count
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            export.status = 'failed'
            export.error_message = str(e)
            export.save()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def grades(self, request):
        """Export grades data"""
        from grades.models import Grade
        from .utils import generate_grades_csv, save_export_file
        
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        export = Export.objects.create(
            teacher=request.user,
            export_type='grades',
            format=serializer.validated_data.get('format', 'csv'),
            filters=serializer.validated_data.get('filters', {}),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        try:
            # Get grades data
            grades = Grade.objects.filter(student__teacher=request.user)
            
            # Apply filters
            filters = export.filters
            if filters:
                if 'start_date' in filters:
                    grades = grades.filter(grade_date__gte=filters['start_date'])
                if 'end_date' in filters:
                    grades = grades.filter(grade_date__lte=filters['end_date'])
                if 'subject' in filters:
                    grades = grades.filter(subject=filters['subject'])
            
            # Generate CSV
            content = generate_grades_csv(grades, export.fields or None)
            filename = f'grades_{export.id}.csv'
            
            # Save file
            export.records_count = grades.count()
            save_export_file(export, content, filename)
            
            return Response({
                'export_id': export.id,
                'status': 'completed',
                'download_url': export.file.url,
                'records_count': export.records_count
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            export.status = 'failed'
            export.error_message = str(e)
            export.save()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def groups(self, request):
        """Export groups data"""
        from groups.models import Group
        from .utils import generate_groups_csv, save_export_file
        
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        export = Export.objects.create(
            teacher=request.user,
            export_type='groups',
            format=serializer.validated_data.get('format', 'csv'),
            filters=serializer.validated_data.get('filters', {}),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        try:
            # Get groups data
            groups = Group.objects.filter(teacher=request.user)
            
            # Apply filters
            filters = export.filters
            if filters:
                if 'is_active' in filters:
                    groups = groups.filter(is_active=filters['is_active'])
                if 'subject' in filters:
                    groups = groups.filter(subject=filters['subject'])
            
            # Generate CSV
            content = generate_groups_csv(groups, export.fields or None)
            filename = f'groups_{export.id}.csv'
            
            # Save file
            export.records_count = groups.count()
            save_export_file(export, content, filename)
            
            return Response({
                'export_id': export.id,
                'status': 'completed',
                'download_url': export.file.url,
                'records_count': export.records_count
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            export.status = 'failed'
            export.error_message = str(e)
            export.save()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get export status"""
        export = self.get_object()
        
        return Response({
            'id': export.id,
            'export_type': export.export_type,
            'status': export.status,
            'download_url': export.file.url if export.file else None,
            'file_size': export.file_size,
            'records_count': export.records_count,
            'generated_at': export.generated_at,
            'expires_at': export.expires_at
        })
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download export file"""
        export = self.get_object()
        
        if not export.file:
            return Response({
                'error': 'Export file not ready yet'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return FileResponse(
            export.file.open('rb'),
            as_attachment=True,
            filename=f"{export.export_type}_{export.id}.{export.format}"
        )

    @action(detail=False, methods=['post'])
    def student_cards(self, request):
        """
        Generate a PDF sheet of student ID cards (3-column grid, RTL, Arabic).

        POST body (JSON):
          {
            "student_ids": ["uuid1", "uuid2", ...],   // specific students
            "group_id": "uuid"                         // OR all students in a group
          }

        At least one of the two must be provided.
        Returns the PDF file as a direct download (application/pdf).
        """
        from students.models import Student
        from django.http import HttpResponse
        from .utils_cards import generate_student_cards_pdf

        student_ids = request.data.get('student_ids', [])
        group_id    = request.data.get('group_id', None)

        if not student_ids and not group_id:
            return Response(
                {'error': 'Provide at least one of: student_ids or group_id.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build queryset — always scoped to the requesting teacher
        qs = Student.objects.filter(
            teacher=request.user, is_active=True
        ).prefetch_related(
            'student_groups__group',
            'parent_links__parent',
        ).select_related('teacher', 'teacher__teacher_profile')

        if group_id:
            qs = qs.filter(student_groups__group_id=group_id, student_groups__is_active=True)

        if student_ids:
            qs = qs.filter(id__in=student_ids)

        students = qs.distinct()

        if not students.exists():
            return Response(
                {'error': 'No students found with the provided IDs.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            pdf_bytes = generate_student_cards_pdf(students)
        except Exception as e:
            return Response(
                {'error': f'PDF generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="student_cards.pdf"'
        response['Content-Length'] = len(pdf_bytes)
        return response

    @action(detail=False, methods=['post'])
    def student_report(self, request):
        """
        Generate a comprehensive PDF report for a single student.

        POST body (JSON) — one of:
          { "student_code": "ST-000001" }
          { "student_id":   "uuid" }

        Returns: PDF file download (application/pdf)
        """
        from students.models import Student
        from django.http import HttpResponse
        from .utils_student_report import generate_student_report_pdf

        student_code = request.data.get('student_code')
        student_id   = request.data.get('student_id')

        if not student_code and not student_id:
            return Response(
                {'error': 'Provide student_code or student_id.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        qs = Student.objects.filter(
            teacher=request.user
        ).prefetch_related(
            'student_groups__group',
            'parent_links__parent',
        ).select_related('teacher', 'teacher__teacher_profile')

        try:
            if student_code:
                student = qs.get(code=student_code)
            else:
                student = qs.get(id=student_id)
        except Student.DoesNotExist:
            return Response(
                {'error': 'Student not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            pdf_bytes = generate_student_report_pdf(student)
        except Exception as e:
            return Response(
                {'error': f'PDF generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        safe_name = (student.name or 'student').replace(' ', '_')
        filename = f"report_{safe_name}_{student.code or student.id}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf_bytes)
        return response
