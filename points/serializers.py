"""
Points Serializers
"""
from rest_framework import serializers
from .models import PointRule, Prize, StudentPoints, PointTransaction


class PointRuleSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(
        source='get_event_type_display', read_only=True
    )
    group_name = serializers.CharField(
        source='group.name', read_only=True, default=None
    )

    class Meta:
        model = PointRule
        fields = [
            'id', 'event_type', 'event_type_display',
            'points', 'description', 'group', 'group_name',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prize
        fields = [
            'id', 'name', 'description', 'points_required',
            'icon', 'color', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StudentPointsSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_code = serializers.CharField(source='student.code', read_only=True)
    student_id = serializers.UUIDField(source='student.id', read_only=True)

    # Next prize info
    next_prize = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    unlocked_prizes = serializers.SerializerMethodField()

    class Meta:
        model = StudentPoints
        fields = [
            'id', 'student_id', 'student_name', 'student_code',
            'total_points', 'total_earned', 'total_deducted',
            'next_prize', 'progress_percent', 'unlocked_prizes',
            'last_updated',
        ]
        read_only_fields = fields

    def _get_prizes_qs(self):
        request = self.context.get('request')
        if not request:
            return Prize.objects.none()
        return Prize.objects.filter(teacher=request.user, is_active=True)

    def get_next_prize(self, obj):
        prizes_qs = self._get_prizes_qs()
        prize = obj.get_next_prize(prizes_qs)
        if prize:
            return {
                'id': str(prize.id),
                'name': prize.name,
                'points_required': prize.points_required,
                'icon': prize.icon,
                'color': prize.color,
            }
        return None

    def get_progress_percent(self, obj):
        prizes_qs = self._get_prizes_qs()
        next_prize = obj.get_next_prize(prizes_qs)
        if not next_prize:
            return 100  # all prizes unlocked

        # Find the previous prize threshold
        prev_prize = prizes_qs.filter(
            points_required__lte=obj.total_points,
            is_active=True
        ).order_by('-points_required').first()

        prev_threshold = prev_prize.points_required if prev_prize else 0
        span = next_prize.points_required - prev_threshold
        earned_in_span = obj.total_points - prev_threshold

        if span <= 0:
            return 0
        return round(min(100, (earned_in_span / span) * 100), 1)

    def get_unlocked_prizes(self, obj):
        prizes_qs = self._get_prizes_qs()
        unlocked = obj.get_unlocked_prizes(prizes_qs)
        return [
            {
                'id': str(p.id),
                'name': p.name,
                'points_required': p.points_required,
                'icon': p.icon,
                'color': p.color,
            }
            for p in unlocked
        ]


class PointTransactionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_code = serializers.CharField(source='student.code', read_only=True)
    event_type_display = serializers.CharField(
        source='get_event_type_display', read_only=True
    )

    class Meta:
        model = PointTransaction
        fields = [
            'id', 'student', 'student_name', 'student_code',
            'points', 'event_type', 'event_type_display',
            'description', 'date',
            'session', 'grade', 'behavior_record',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    student_id = serializers.UUIDField()
    student_name = serializers.CharField()
    student_code = serializers.CharField()
    total_points = serializers.IntegerField()
    total_earned = serializers.IntegerField()
    total_deducted = serializers.IntegerField()
    next_prize_name = serializers.CharField(allow_null=True)
    next_prize_points = serializers.IntegerField(allow_null=True)
    progress_percent = serializers.FloatField()


class AwardPointsSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    points = serializers.IntegerField(help_text='موجب للمكافأة، سالب للخصم')
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    event_type = serializers.ChoiceField(
        choices=PointRule.EVENT_TYPES,
        default='manual'
    )
    date = serializers.DateField(required=False)
