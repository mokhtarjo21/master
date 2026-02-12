"""
Grade Serializers
"""
from rest_framework import serializers
from decimal import Decimal
from .models import GradeType, Grade, GradeScale, GradeSummary, GradeAlert, GradeComment


class GradeTypeSerializer(serializers.ModelSerializer):
    """Grade type serializer"""
    grades_count = serializers.SerializerMethodField()
    
    class Meta:
        model = GradeType
        fields = [
            'id', 'name', 'description', 'max_score', 'min_score',
            'weight', 'color', 'icon', 'is_active', 'grades_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'teacher', 'grades_count', 'created_at', 'updated_at']
    
    def get_grades_count(self, obj):
        return obj.grades.filter(is_active=True).count()
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return GradeType.objects.create(**validated_data)


class GradeCommentSerializer(serializers.ModelSerializer):
    """Grade comment serializer"""
    author_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = GradeComment
        fields = [
            'id', 'comment', 'is_private', 'author_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'grade', 'created_by', 'created_at', 'updated_at']


class GradeSerializer(serializers.ModelSerializer):
    """Main grade serializer"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_code = serializers.CharField(source='student.code', read_only=True)
    grade_type_name = serializers.CharField(source='grade_type.name', read_only=True)
    grade_type_color = serializers.CharField(source='grade_type.color', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    grade_status = serializers.SerializerMethodField()
    comments = GradeCommentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Grade
        fields = [
            'id', 'student', 'student_name', 'student_code',
            'grade_type', 'grade_type_name', 'grade_type_color',
            'session', 'session_title', 'title', 'description',
            'score', 'max_score', 'percentage', 'letter_grade',
            'grade_date', 'notes', 'feedback', 'grade_status',
            'is_active', 'is_published', 'comments',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'percentage', 'letter_grade', 'grade_status',
            'created_at', 'updated_at'
        ]
    
    def get_grade_status(self, obj):
        return obj.get_grade_status()
    
    def validate(self, data):
        # Ensure teacher owns the student
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            student = data.get('student')
            if student and student.teacher != request.user:
                raise serializers.ValidationError("You can only create grades for your own students")
            
            # Ensure teacher owns the grade type
            grade_type = data.get('grade_type')
            if grade_type and grade_type.teacher != request.user:
                raise serializers.ValidationError("You can only use your own grade types")
        
        # Validate score range
        score = data.get('score')
        max_score = data.get('max_score')
        
        if score and max_score and score > max_score:
            raise serializers.ValidationError("Score cannot exceed max score")
        
        if score and score < 0:
            raise serializers.ValidationError("Score cannot be negative")
        
        return data
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return Grade.objects.create(**validated_data)


class GradeCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for grade creation"""
    
    class Meta:
        model = Grade
        fields = [
            'student', 'grade_type', 'session', 'title', 'description',
            'score', 'max_score', 'grade_date', 'notes', 'feedback',
            'is_published'
        ]
    
    def validate(self, data):
        # Same validation as GradeSerializer
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            student = data.get('student')
            if student and student.teacher != request.user:
                raise serializers.ValidationError("You can only create grades for your own students")
            
            grade_type = data.get('grade_type')
            if grade_type and grade_type.teacher != request.user:
                raise serializers.ValidationError("You can only use your own grade types")
        
        score = data.get('score')
        max_score = data.get('max_score')
        
        if score and max_score and score > max_score:
            raise serializers.ValidationError("Score cannot exceed max score")
        
        if score and score < 0:
            raise serializers.ValidationError("Score cannot be negative")
        
        return data
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return Grade.objects.create(**validated_data)


class GradeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for grade lists"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    grade_type_name = serializers.CharField(source='grade_type.name', read_only=True)
    grade_type_color = serializers.CharField(source='grade_type.color', read_only=True)
    
    class Meta:
        model = Grade
        fields = [
            'id', 'student_name', 'grade_type_name', 'grade_type_color',
            'title', 'score', 'max_score', 'percentage', 'letter_grade',
            'grade_date', 'is_published'
        ]


class GradeScaleSerializer(serializers.ModelSerializer):
    """Grade scale serializer"""
    
    class Meta:
        model = GradeScale
        fields = [
            'id', 'name', 'description', 'scale_data',
            'is_active', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return GradeScale.objects.create(**validated_data)


class GradeSummarySerializer(serializers.ModelSerializer):
    """Grade summary serializer"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_code = serializers.CharField(source='student.code', read_only=True)
    grade_status = serializers.SerializerMethodField()
    
    class Meta:
        model = GradeSummary
        fields = [
            'id', 'student', 'student_name', 'student_code',
            'summary_type', 'period_start', 'period_end',
            'total_grades', 'average_score', 'average_percentage',
            'overall_letter_grade', 'grade_type_averages',
            'class_rank', 'total_students', 'improvement_trend',
            'grade_status', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_grades', 'average_score', 'average_percentage',
            'overall_letter_grade', 'grade_type_averages', 'class_rank',
            'total_students', 'improvement_trend', 'grade_status',
            'created_at', 'updated_at'
        ]
    
    def get_grade_status(self, obj):
        if obj.average_percentage >= 90:
            return 'Excellent'
        elif obj.average_percentage >= 80:
            return 'Very Good'
        elif obj.average_percentage >= 70:
            return 'Good'
        elif obj.average_percentage >= 60:
            return 'Satisfactory'
        else:
            return 'Needs Improvement'


class GradeAlertSerializer(serializers.ModelSerializer):
    """Grade alert serializer"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_code = serializers.CharField(source='student.code', read_only=True)
    grade_title = serializers.CharField(source='grade.title', read_only=True)
    
    class Meta:
        model = GradeAlert
        fields = [
            'id', 'student', 'student_name', 'student_code',
            'grade', 'grade_title', 'alert_type', 'severity',
            'title', 'message', 'trigger_data', 'is_active',
            'is_resolved', 'resolved_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'trigger_data', 'resolved_at', 'created_at'
        ]


class BulkGradeSerializer(serializers.Serializer):
    """Serializer for bulk grade operations"""
    grades = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    
    def validate_grades(self, value):
        required_fields = ['student_id', 'grade_type_id', 'title', 'score', 'max_score']
        
        for grade_data in value:
            for field in required_fields:
                if field not in grade_data:
                    raise serializers.ValidationError(f"Field '{field}' is required for each grade")
            
            # Validate score
            try:
                score = Decimal(str(grade_data['score']))
                max_score = Decimal(str(grade_data['max_score']))
                
                if score < 0:
                    raise serializers.ValidationError("Score cannot be negative")
                if score > max_score:
                    raise serializers.ValidationError("Score cannot exceed max score")
                    
            except (ValueError, TypeError):
                raise serializers.ValidationError("Invalid score or max_score value")
        
        return value


class StudentGradeReportSerializer(serializers.Serializer):
    """Serializer for student grade reports"""
    student_id = serializers.UUIDField()
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    grade_types = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    include_comments = serializers.BooleanField(default=True)
    include_summary = serializers.BooleanField(default=True)
    
    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Start date must be before end date")
        
        return data