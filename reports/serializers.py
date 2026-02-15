"""
Reports Serializers
"""
from rest_framework import serializers
from .models import Report, ReportTemplate


class ReportSerializer(serializers.ModelSerializer):
    """Report serializer"""
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = [
            'id', 'report_type', 'title', 'description',
            'period_start', 'period_end', 'file', 'format',
            'status', 'error_message', 'filters', 'options',
            'download_url', 'generated_at', 'expires_at', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'file', 'generated_at', 'created_at']
    
    def get_download_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class ReportRequestSerializer(serializers.Serializer):
    """Serializer for report generation requests"""
    report_type = serializers.ChoiceField(choices=Report.REPORT_TYPES)
    format = serializers.ChoiceField(choices=Report.FORMAT_CHOICES, default='pdf')
    period_start = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)
    filters = serializers.JSONField(required=False, default=dict)
    options = serializers.JSONField(required=False, default=dict)


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Report template serializer"""
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'report_type', 'template_config',
            'is_default', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
