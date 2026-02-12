"""
Grade Views
"""
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Avg, Count, Max, Min
from django.utils import timezone
from datetime import date, timedelta
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsTeacher, ReadOnlyForStudentsAndParents
from .models import GradeType, Grade, GradeScale, GradeSummary, GradeAlert, GradeComment
from .serializers import (
    GradeTypeSerializer, GradeSerializer, GradeCreateSerializer,
    GradeListSerializer, GradeScaleSerializer, GradeSummarySerializer,
    GradeAlertSerializer, GradeCommentSerializer, BulkGradeSerializer,
    StudentGradeReportSerializer
)


class GradeTypeViewSet(viewsets.ModelViewSet):
    """Grade type management"""
    serializer_class = GradeTypeSerializer
    permission_classes = [IsTeacher]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'weight', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        return GradeType.objects.filter(teacher=self.request.user)
    
    @action(detail=False, methods=['post'])
    def create_default_types(self, request):
        """Create default grade types"""
        default_types = [
            {'name': 'Quiz', 'description': 'Short quizzes', 'weight': 0.2, 'color': '#17a2b8'},
            {'name': 'Assignment', 'description': 'Homework assignments', 'weight': 0.3, 'color': '#28a745'},
            {'name': 'Exam', 'description': 'Major exams', 'weight': 0.4, 'color': '#dc3545'},
            {'name': 'Participation', 'description': 'Class participation', 'weight': 0.1, 'color': '#ffc107'},
        ]
        
        created_types = []
        for type_data in default_types:
            grade_type, created = GradeType.objects.get_or_create(
                teacher=request.user,
                name=type_data['name'],
                defaults=type_data
            )
            if created:
                created_types.append(grade_type)
        
        serializer = GradeTypeSerializer(created_types, many=True)
        return Response({
            'message': f'Created {len(created_types)} default grade types',
            'created_types': serializer.data
        })


class GradeViewSet(viewsets.ModelViewSet):
    """Grade management viewset"""
    permission_classes = [ReadOnlyForStudentsAndParents]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['grade_type', 'student', 'session', 'is_published']
    search_fields = ['title', 'student__name', 'student__code']
    ordering_fields = ['grade_date', 'score', 'percentage', 'created_at']
    ordering = ['-grade_date', '-created_at']
    
    def get_queryset(self):
        if self.request.user.user_type == 'teacher':
            return Grade.objects.filter(
                student__teacher=self.request.user,
                is_active=True
            ).select_related('student', 'grade_type', 'session')
        elif self.request.user.user_type == 'student':
            return Grade.objects.filter(
                student__user=self.request.user,
                is_active=True,
                is_published=True
            ).select_related('grade_type', 'session')
        elif self.request.user.user_type == 'parent':
            from students.models import StudentParentLink
            linked_student_ids = StudentParentLink.objects.filter(
                parent__user=self.request.user,
                is_active=True,
                can_view_grades=True
            ).values_list('student_id', flat=True)
            
            return Grade.objects.filter(
                student_id__in=linked_student_ids,
                is_active=True,
                is_published=True
            ).select_related('student', 'grade_type', 'session')
        
        return Grade.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return GradeCreateSerializer
        elif self.action == 'list':
            return GradeListSerializer
        return GradeSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new grade"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can create grades'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            grade = serializer.save()
            response_serializer = GradeSerializer(grade)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create grades"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can create grades'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BulkGradeSerializer(data=request.data)
        if serializer.is_valid():
            grades_data = serializer.validated_data['grades']
            
            created_grades = []
            errors = []
            
            for grade_data in grades_data:
                try:
                    # Validate student and grade type ownership
                    from students.models import Student
                    student = Student.objects.get(
                        id=grade_data['student_id'],
                        teacher=request.user
                    )
                    
                    grade_type = GradeType.objects.get(
                        id=grade_data['grade_type_id'],
                        teacher=request.user
                    )
                    
                    # Create grade
                    grade = Grade.objects.create(
                        student=student,
                        grade_type=grade_type,
                        title=grade_data['title'],
                        description=grade_data.get('description', ''),
                        score=grade_data['score'],
                        max_score=grade_data['max_score'],
                        grade_date=grade_data.get('grade_date', timezone.now().date()),
                        notes=grade_data.get('notes', ''),
                        feedback=grade_data.get('feedback', ''),
                        is_published=grade_data.get('is_published', True),
                        created_by=request.user
                    )
                    
                    created_grades.append(grade)
                    
                except Exception as e:
                    errors.append(f"Error creating grade for student {grade_data.get('student_id')}: {str(e)}")
            
            return Response({
                'message': f'Created {len(created_grades)} grades',
                'created_count': len(created_grades),
                'errors': errors
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """Add comment to grade"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can add comments'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        grade = self.get_object()
        serializer = GradeCommentSerializer(data=request.data)
        
        if serializer.is_valid():
            comment = serializer.save(
                grade=grade,
                created_by=request.user
            )
            return Response(GradeCommentSerializer(comment).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def student_grades(self, request):
        """Get grades for a specific student"""
        student_id = request.query_params.get('student_id')
        if not student_id:
            return Response(
                {'error': 'student_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(student_id=student_id)
        
        # Apply filters
        grade_type_id = request.query_params.get('grade_type')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if grade_type_id:
            queryset = queryset.filter(grade_type_id=grade_type_id)
        if start_date:
            queryset = queryset.filter(grade_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(grade_date__lte=end_date)
        
        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = GradeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = GradeSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get grade statistics"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can view statistics'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        
        # Apply filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        grade_type_id = request.query_params.get('grade_type')
        
        if start_date:
            queryset = queryset.filter(grade_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(grade_date__lte=end_date)
        if grade_type_id:
            queryset = queryset.filter(grade_type_id=grade_type_id)
        
        # Calculate statistics
        stats = queryset.aggregate(
            total_grades=Count('id'),
            average_score=Avg('score'),
            average_percentage=Avg('percentage'),
            highest_score=Max('score'),
            lowest_score=Min('score')
        )
        
        # Grade distribution
        grade_distribution = {}
        for letter in ['A+', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'F']:
            count = queryset.filter(letter_grade=letter).count()
            grade_distribution[letter] = count
        
        stats['grade_distribution'] = grade_distribution
        
        # Grade type breakdown
        grade_type_stats = queryset.values('grade_type__name').annotate(
            count=Count('id'),
            avg_percentage=Avg('percentage')
        ).order_by('grade_type__name')
        
        stats['grade_type_breakdown'] = list(grade_type_stats)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent grades"""
        days = int(request.query_params.get('days', 7))
        since_date = timezone.now().date() - timedelta(days=days)
        
        queryset = self.get_queryset().filter(grade_date__gte=since_date)
        serializer = GradeListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def generate_report(self, request):
        """Generate student grade report"""
        serializer = StudentGradeReportSerializer(data=request.data)
        if serializer.is_valid():
            student_id = serializer.validated_data['student_id']
            start_date = serializer.validated_data.get('start_date')
            end_date = serializer.validated_data.get('end_date')
            grade_types = serializer.validated_data.get('grade_types', [])
            include_comments = serializer.validated_data.get('include_comments', True)
            include_summary = serializer.validated_data.get('include_summary', True)
            
            # Get student grades
            grades_qs = self.get_queryset().filter(student_id=student_id)
            
            if start_date:
                grades_qs = grades_qs.filter(grade_date__gte=start_date)
            if end_date:
                grades_qs = grades_qs.filter(grade_date__lte=end_date)
            if grade_types:
                grades_qs = grades_qs.filter(grade_type_id__in=grade_types)
            
            # Serialize grades
            grades_data = GradeSerializer(grades_qs, many=True).data
            
            # Calculate summary if requested
            summary_data = None
            if include_summary and grades_qs.exists():
                summary_data = {
                    'total_grades': grades_qs.count(),
                    'average_percentage': grades_qs.aggregate(avg=Avg('percentage'))['avg'],
                    'highest_score': grades_qs.aggregate(max=Max('score'))['max'],
                    'lowest_score': grades_qs.aggregate(min=Min('score'))['min'],
                    'grade_distribution': {}
                }
                
                # Grade distribution
                for letter in ['A+', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'F']:
                    count = grades_qs.filter(letter_grade=letter).count()
                    summary_data['grade_distribution'][letter] = count
            
            return Response({
                'student_id': student_id,
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'grades': grades_data,
                'summary': summary_data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GradeScaleViewSet(viewsets.ModelViewSet):
    """Grade scale management"""
    serializer_class = GradeScaleSerializer
    permission_classes = [IsTeacher]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        return GradeScale.objects.filter(teacher=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set grade scale as default"""
        scale = self.get_object()
        scale.is_default = True
        scale.save()
        
        serializer = GradeScaleSerializer(scale)
        return Response(serializer.data)


class GradeSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """Grade summary viewset"""
    serializer_class = GradeSummarySerializer
    permission_classes = [ReadOnlyForStudentsAndParents]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['summary_type', 'student']
    ordering_fields = ['period_start', 'average_percentage']
    ordering = ['-period_start']
    
    def get_queryset(self):
        if self.request.user.user_type == 'teacher':
            return GradeSummary.objects.filter(
                student__teacher=self.request.user
            ).select_related('student')
        elif self.request.user.user_type == 'student':
            return GradeSummary.objects.filter(
                student__user=self.request.user
            )
        elif self.request.user.user_type == 'parent':
            from students.models import StudentParentLink
            linked_student_ids = StudentParentLink.objects.filter(
                parent__user=self.request.user,
                is_active=True,
                can_view_grades=True
            ).values_list('student_id', flat=True)
            
            return GradeSummary.objects.filter(
                student_id__in=linked_student_ids
            ).select_related('student')
        
        return GradeSummary.objects.none()
    
    @action(detail=False, methods=['post'])
    def generate_monthly(self, request):
        """Generate monthly summaries"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can generate summaries'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        year = int(request.data.get('year', timezone.now().year))
        month = int(request.data.get('month', timezone.now().month))
        
        # Calculate period
        period_start = date(year, month, 1)
        if month == 12:
            period_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = date(year, month + 1, 1) - timedelta(days=1)
        
        # Get students
        from students.models import Student
        students = Student.objects.filter(
            teacher=request.user,
            is_active=True
        )
        
        summaries_created = 0
        
        for student in students:
            summary, created = GradeSummary.objects.get_or_create(
                student=student,
                summary_type='monthly',
                period_start=period_start,
                period_end=period_end
            )
            
            if created or not summary.total_grades:
                summary.calculate_summary()
                summaries_created += 1
        
        return Response({
            'message': f'Generated {summaries_created} monthly summaries',
            'period': f'{year}-{month:02d}',
            'summaries_created': summaries_created
        })


class GradeAlertViewSet(viewsets.ModelViewSet):
    """Grade alert viewset"""
    serializer_class = GradeAlertSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['alert_type', 'severity', 'is_active', 'is_resolved']
    ordering_fields = ['created_at', 'severity']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return GradeAlert.objects.filter(
            student__teacher=self.request.user
        ).select_related('student', 'grade')
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a grade alert"""
        alert = self.get_object()
        alert.resolve(resolved_by=request.user)
        
        serializer = GradeAlertSerializer(alert)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_resolve(self, request):
        """Bulk resolve grade alerts"""
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