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
        
        # TODO: Trigger async task to generate export
        
        return Response({
            'export_id': export.id,
            'status': 'processing',
            'estimated_completion': timezone.now() + timedelta(minutes=1)
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=False, methods=['post'])
    def payments(self, request):
        """Export payments data"""
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        export = Export.objects.create(
            teacher=request.user,
            export_type='payments',
            format=serializer.validated_data.get('format', 'csv'),
            filters=serializer.validated_data.get('filters', {}),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        return Response({
            'export_id': export.id,
            'status': 'processing'
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=False, methods=['post'])
    def attendance(self, request):
        """Export attendance data"""
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        export = Export.objects.create(
            teacher=request.user,
            export_type='attendance',
            format=serializer.validated_data.get('format', 'csv'),
            filters=serializer.validated_data.get('filters', {}),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        return Response({
            'export_id': export.id,
            'status': 'processing'
        }, status=status.HTTP_202_ACCEPTED)
    
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
