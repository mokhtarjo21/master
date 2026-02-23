"""
Behavior Assessment Views
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Avg, Count
from django_filters.rest_framework import DjangoFilterBackend
from accounts.permissions import IsTeacher
from .models import BehaviorCategory, BehaviorRecord, BehaviorSummary
from .serializers import (
    BehaviorCategorySerializer,
    BehaviorRecordSerializer,
    BehaviorRecordListSerializer,
    BehaviorSummarySerializer,
)


class BehaviorCategoryViewSet(viewsets.ModelViewSet):
    """CRUD for behavior categories (configurable per teacher)"""
    serializer_class = BehaviorCategorySerializer
    permission_classes = [IsTeacher]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'name_en']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        return BehaviorCategory.objects.filter(teacher=self.request.user)


class BehaviorRecordViewSet(viewsets.ModelViewSet):
    """CRUD for behavioral assessment records"""
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['student', 'category', 'rating', 'session', 'parent_notified']
    search_fields = ['student__name', 'student__code', 'notes']
    ordering_fields = ['date', 'created_at', 'score']
    ordering = ['-date']

    def get_queryset(self):
        qs = BehaviorRecord.objects.filter(
            teacher=self.request.user
        ).select_related('student', 'category', 'session')

        # Extra filters
        group_id = self.request.query_params.get('group_id')
        if group_id:
            qs = qs.filter(
                student__student_groups__group_id=group_id,
                student__student_groups__is_active=True
            )

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

        return qs.distinct()

    def get_serializer_class(self):
        if self.action == 'list':
            return BehaviorRecordListSerializer
        return BehaviorRecordSerializer

    # ── Extra actions ────────────────────────────────────────────────────────

    @action(detail=True, methods=['post'])
    def notify_parent(self, request, pk=None):
        """Manually trigger parent WhatsApp notification for this record."""
        record = self.get_object()
        if record.parent_notified:
            return Response(
                {'message': 'Parent already notified.', 'notified_at': record.notified_at},
                status=status.HTTP_200_OK
            )
        success = record.notify_parent()
        if success:
            return Response({'message': 'Notification queued successfully.'})
        return Response(
            {'error': 'No phone number available for parent or student.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Create behavior records for multiple students at once.

        POST body:
        {
            "student_ids": ["uuid1", "uuid2"],
            "category": "uuid",            // optional
            "session": "uuid",             // optional
            "rating": "good",
            "notes": "...",
            "date": "2026-02-23"           // optional, defaults to today
        }
        """
        from students.models import Student
        from django.utils import timezone

        student_ids = request.data.get('student_ids', [])
        if not student_ids:
            return Response(
                {'error': 'student_ids is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rating = request.data.get('rating')
        if not rating or rating not in dict(BehaviorRecord.RATING_CHOICES):
            return Response(
                {'error': f'Valid rating is required. Choices: {list(dict(BehaviorRecord.RATING_CHOICES).keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        students = Student.objects.filter(
            id__in=student_ids,
            teacher=request.user,
            is_active=True
        )
        if not students.exists():
            return Response({'error': 'No valid students found.'}, status=status.HTTP_404_NOT_FOUND)

        # Resolve optional FK fields
        category = None
        category_id = request.data.get('category')
        if category_id:
            try:
                category = BehaviorCategory.objects.get(id=category_id, teacher=request.user)
            except BehaviorCategory.DoesNotExist:
                return Response({'error': 'Category not found.'}, status=status.HTTP_400_BAD_REQUEST)

        session = None
        session_id = request.data.get('session')
        if session_id:
            from teaching_sessions.models import Session
            try:
                session = Session.objects.get(id=session_id, group__teacher=request.user)
            except Session.DoesNotExist:
                return Response({'error': 'Session not found.'}, status=status.HTTP_400_BAD_REQUEST)

        date_str = request.data.get('date')
        from datetime import date
        if date_str:
            from datetime import datetime
            try:
                record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            record_date = date.today()

        notes = request.data.get('notes', '')

        created_records = []
        for student in students:
            record = BehaviorRecord.objects.create(
                teacher=request.user,
                student=student,
                category=category,
                session=session,
                rating=rating,
                notes=notes,
                date=record_date,
                created_by=request.user,
            )
            # Auto-notify if negative
            should_notify = True
            if category:
                should_notify = category.notify_on_negative
            if record.is_negative and should_notify:
                record.notify_parent()

            created_records.append(record)

        return Response(
            {
                'created': len(created_records),
                'records': BehaviorRecordListSerializer(created_records, many=True).data
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Summary statistics for teacher's behavior records.
        Query params: group_id, start_date, end_date, student_id
        """
        qs = self.get_queryset()

        student_id = request.query_params.get('student_id')
        if student_id:
            qs = qs.filter(student_id=student_id)

        agg = qs.aggregate(
            total=Count('id'),
            avg_score=Avg('score'),
            excellent=Count('id', filter=Q(rating='excellent')),
            good=Count('id', filter=Q(rating='good')),
            satisfactory=Count('id', filter=Q(rating='satisfactory')),
            needs_improvement=Count('id', filter=Q(rating='needs_improvement')),
            poor=Count('id', filter=Q(rating='poor')),
            notified=Count('id', filter=Q(parent_notified=True)),
        )

        # Per-student ranking (top 5 lowest)
        low_students = (
            qs.values('student__id', 'student__name')
            .annotate(avg=Avg('score'), cnt=Count('id'))
            .filter(avg__lt=3)
            .order_by('avg')[:5]
        )

        return Response({
            'total_records': agg['total'],
            'average_score': round(agg['avg_score'] or 0, 2),
            'by_rating': {
                'excellent': agg['excellent'],
                'good': agg['good'],
                'satisfactory': agg['satisfactory'],
                'needs_improvement': agg['needs_improvement'],
                'poor': agg['poor'],
            },
            'parents_notified': agg['notified'],
            'students_needing_attention': list(low_students),
        })


class BehaviorSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only summaries (generated via calculate())"""
    serializer_class = BehaviorSummarySerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['student', 'summary_type']
    ordering_fields = ['period_start']
    ordering = ['-period_start']

    def get_queryset(self):
        return BehaviorSummary.objects.filter(
            student__teacher=self.request.user
        ).select_related('student')

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generate/refresh summary for a student and period.
        POST: { "student_id": "uuid", "summary_type": "monthly",
                "period_start": "2026-02-01", "period_end": "2026-02-28" }
        """
        from students.models import Student
        from datetime import datetime

        student_id = request.data.get('student_id')
        summary_type = request.data.get('summary_type', 'monthly')
        period_start_str = request.data.get('period_start')
        period_end_str = request.data.get('period_end')

        if not all([student_id, period_start_str, period_end_str]):
            return Response(
                {'error': 'student_id, period_start, period_end are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student = Student.objects.get(id=student_id, teacher=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date()
            period_end   = datetime.strptime(period_end_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Use YYYY-MM-DD format.'}, status=status.HTTP_400_BAD_REQUEST)

        summary, _ = BehaviorSummary.objects.get_or_create(
            student=student,
            summary_type=summary_type,
            period_start=period_start,
            defaults={'period_end': period_end}
        )
        summary.period_end = period_end
        summary.calculate()

        return Response(BehaviorSummarySerializer(summary).data)
