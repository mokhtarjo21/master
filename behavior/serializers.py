"""
Behavior Assessment Serializers
"""
from rest_framework import serializers
from .models import BehaviorCategory, BehaviorRecord, BehaviorSummary


class BehaviorCategorySerializer(serializers.ModelSerializer):
    records_count = serializers.SerializerMethodField()

    class Meta:
        model = BehaviorCategory
        fields = [
            'id', 'name', 'name_en', 'icon', 'color',
            'notify_on_negative', 'is_active',
            'records_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_records_count(self, obj):
        return obj.records.count()

    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return super().create(validated_data)


class BehaviorRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_code = serializers.CharField(source='student.code', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    rating_display = serializers.CharField(source='get_rating_display', read_only=True)
    is_negative = serializers.BooleanField(read_only=True)

    class Meta:
        model = BehaviorRecord
        fields = [
            'id', 'student', 'student_name', 'student_code',
            'category', 'category_name', 'session',
            'rating', 'rating_display', 'score',
            'notes', 'date', 'is_negative',
            'parent_notified', 'notified_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'score', 'is_negative',
            'parent_notified', 'notified_at',
            'created_at', 'updated_at',
        ]

    def validate(self, data):
        request = self.context.get('request')
        student = data.get('student')
        if student and student.teacher != request.user:
            raise serializers.ValidationError(
                {'student': 'Student does not belong to you.'}
            )
        category = data.get('category')
        if category and category.teacher != request.user:
            raise serializers.ValidationError(
                {'category': 'Category does not belong to you.'}
            )
        return data

    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        validated_data['created_by'] = self.context['request'].user
        record = super().create(validated_data)

        # Auto-notify parent for negative ratings if category allows it
        should_notify = True
        if record.category:
            should_notify = record.category.notify_on_negative

        if record.is_negative and should_notify:
            record.notify_parent()

        return record


class BehaviorRecordListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    rating_display = serializers.CharField(source='get_rating_display', read_only=True)

    class Meta:
        model = BehaviorRecord
        fields = [
            'id', 'student', 'student_name',
            'category_name', 'rating', 'rating_display',
            'score', 'date', 'parent_notified',
        ]


class BehaviorSummarySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)

    class Meta:
        model = BehaviorSummary
        fields = [
            'id', 'student', 'student_name',
            'summary_type', 'period_start', 'period_end',
            'total_records', 'average_score',
            'excellent_count', 'good_count', 'satisfactory_count',
            'needs_improvement_count', 'poor_count',
            'category_scores', 'created_at', 'updated_at',
        ]
        read_only_fields = fields
