"""
Points Views
CRUD for PointRule, Prize + Leaderboard + Student Summary + Manual Award
"""
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PointRule, Prize, StudentPoints, PointTransaction
from .serializers import (
    PointRuleSerializer,
    PrizeSerializer,
    StudentPointsSerializer,
    PointTransactionSerializer,
    LeaderboardEntrySerializer,
    AwardPointsSerializer,
)


# ---------------------------------------------------------------------------
# PointRule CRUD
# ---------------------------------------------------------------------------
class PointRuleViewSet(viewsets.ModelViewSet):
    serializer_class = PointRuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PointRule.objects.filter(teacher=self.request.user).select_related('group')

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx


# ---------------------------------------------------------------------------
# Prize CRUD
# ---------------------------------------------------------------------------
class PrizeViewSet(viewsets.ModelViewSet):
    serializer_class = PrizeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Prize.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


# ---------------------------------------------------------------------------
# Point Transactions (read + manual create)
# ---------------------------------------------------------------------------
class PointTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PointTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = PointTransaction.objects.filter(
            teacher=self.request.user
        ).select_related('student', 'session', 'grade', 'behavior_record')

        student_id = self.request.query_params.get('student_id')
        event_type = self.request.query_params.get('event_type')
        group_id = self.request.query_params.get('group_id')

        if student_id:
            qs = qs.filter(student_id=student_id)
        if event_type:
            qs = qs.filter(event_type=event_type)
        if group_id:
            qs = qs.filter(student__student_groups__group_id=group_id,
                           student__student_groups__is_active=True).distinct()
        return qs


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------
class LeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Query params:
          ?group_id=<uuid>       → rank within a specific group
          ?grade_level=<str>     → rank across a grade level (group.grade_level)
          ?limit=<int>           → top N students (default 50)
        """
        teacher = request.user
        group_id = request.query_params.get('group_id')
        grade_level = request.query_params.get('grade_level')
        limit = int(request.query_params.get('limit', 50))

        qs = StudentPoints.objects.filter(teacher=teacher).select_related('student')

        if group_id:
            qs = qs.filter(
                student__student_groups__group_id=group_id,
                student__student_groups__is_active=True
            ).distinct()
        elif grade_level:
            qs = qs.filter(
                student__student_groups__group__grade_level=grade_level,
                student__student_groups__is_active=True
            ).distinct()

        qs = qs.order_by('-total_points')[:limit]

        prizes_qs = Prize.objects.filter(teacher=teacher, is_active=True)

        results = []
        for rank, sp in enumerate(qs, start=1):
            next_prize = sp.get_next_prize(prizes_qs)
            prev_prize = prizes_qs.filter(
                points_required__lte=sp.total_points
            ).order_by('-points_required').first()

            prev_threshold = prev_prize.points_required if prev_prize else 0
            if next_prize:
                span = next_prize.points_required - prev_threshold
                earned_in_span = sp.total_points - prev_threshold
                progress = round(min(100, (earned_in_span / span) * 100), 1) if span > 0 else 0
            else:
                progress = 100.0

            results.append({
                'rank': rank,
                'student_id': sp.student.id,
                'student_name': sp.student.name,
                'student_code': sp.student.code,
                'total_points': sp.total_points,
                'total_earned': sp.total_earned,
                'total_deducted': sp.total_deducted,
                'next_prize_name': next_prize.name if next_prize else None,
                'next_prize_points': next_prize.points_required if next_prize else None,
                'progress_percent': progress,
            })

        serializer = LeaderboardEntrySerializer(results, many=True)
        return Response({
            'count': len(results),
            'group_id': group_id,
            'grade_level': grade_level,
            'results': serializer.data
        })


# ---------------------------------------------------------------------------
# Student Summary
# ---------------------------------------------------------------------------
class StudentSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        sp = get_object_or_404(
            StudentPoints,
            student_id=student_id,
            teacher=request.user
        )
        serializer = StudentPointsSerializer(sp, context={'request': request})

        # Recent transactions (last 20)
        transactions = PointTransaction.objects.filter(
            student_id=student_id,
            teacher=request.user
        ).order_by('-created_at')[:20]
        tx_serializer = PointTransactionSerializer(transactions, many=True)

        return Response({
            'summary': serializer.data,
            'recent_transactions': tx_serializer.data,
        })


# ---------------------------------------------------------------------------
# Manual Award / Deduct
# ---------------------------------------------------------------------------
class AwardPointsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AwardPointsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from students.models import Student
        student = get_object_or_404(Student, id=data['student_id'], teacher=request.user)

        points = data['points']
        event_type = data.get('event_type', 'manual')
        description = data.get('description', '')
        date = data.get('date', timezone.now().date())

        # Update balance
        sp, _ = StudentPoints.objects.get_or_create(
            student=student,
            teacher=request.user,
            defaults={'total_points': 0}
        )
        sp.add_points(points)

        # Create transaction
        tx = PointTransaction.objects.create(
            student=student,
            teacher=request.user,
            points=points,
            event_type=event_type,
            description=description,
            date=date,
        )

        return Response({
            'message': 'تم تسجيل النقاط بنجاح',
            'transaction': PointTransactionSerializer(tx).data,
            'new_balance': sp.total_points,
        }, status=status.HTTP_201_CREATED)
