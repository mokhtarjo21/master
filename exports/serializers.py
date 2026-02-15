"""
Exports Serializers
"""
from rest_framework import serializers
from .models import Export


class ExportSerializer(serializers.ModelSerializer):
    """Export serializer"""
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Export
        fields = [
            'id', 'export_type', 'format', 'status',
            'file', 'file_size', 'records_count',
            'filters', 'fields', 'error_message',
            'download_url', 'generated_at', 'expires_at', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'file', 'file_size', 'records_count', 'generated_at']
    
    def get_download_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class ExportRequestSerializer(serializers.Serializer):
    """Export request serializer"""
    format = serializers.ChoiceField(choices=Export.FORMAT_CHOICES, default='csv')
    filters = serializers.JSONField(required=False, default=dict)
    fields = serializers.JSONField(required=False, default=list)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
