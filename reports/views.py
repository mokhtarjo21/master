"""
Reports Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from accounts.permissions import IsTeacher
from .models import Report, ReportTemplate
from .serializers import ReportSerializer, ReportRequestSerializer, ReportTemplateSerializer


class ReportViewSet(viewsets.ModelViewSet):
    """Report management viewset"""
    serializer_class = ReportSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return Report.objects.filter(teacher=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)
    
    @action(detail=False, methods=['post'])
    def student_report(self, request):
        """Generate student report"""
        serializer = ReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create report record
        report = Report.objects.create(
            teacher=request.user,
            report_type='student_report',
            title=f"Student Report - {timezone.now().strftime('%Y-%m-%d')}",
            format=serializer.validated_data.get('format', 'pdf'),
            period_start=serializer.validated_data.get('period_start'),
            period_end=serializer.validated_data.get('period_end'),
            filters=serializer.validated_data.get('filters', {}),
            options=serializer.validated_data.get('options', {}),
            status='generating',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        # TODO: Trigger async task to generate report
        # For now, just return the report ID
        
        return Response({
            'report_id': report.id,
            'status': 'generating',
            'estimated_completion': timezone.now() + timedelta(minutes=2)
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get report generation status"""
        report = self.get_object()
        
        return Response({
            'id': report.id,
            'status': report.status,
            'download_url': report.file.url if report.file else None,
            'generated_at': report.generated_at,
            'expires_at': report.expires_at,
            'error_message': report.error_message
        })
    
    @action(detail=False, methods=['get'])
    def financial(self, request):
        """Generate financial report"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        format_type = request.query_params.get('format', 'json')
        
        if format_type == 'json':
            # Return JSON data directly
            from payments.models import Payment
            from django.db.models import Sum, Count
            
            payments = Payment.objects.filter(
                student__teacher=request.user,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            )
            
            summary = {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'summary': {
                    'total_revenue': payments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0,
                    'total_payments': payments.count(),
                    'pending_amount': payments.aggregate(Sum('remaining_amount'))['remaining_amount__sum'] or 0,
                },
                'by_payment_type': {}
            }
            
            return Response(summary)
        else:
            # Generate PDF/CSV report
            report = Report.objects.create(
                teacher=request.user,
                report_type='monthly_financial',
                title=f"Financial Report - {start_date} to {end_date}",
                format=format_type,
                period_start=start_date,
                period_end=end_date,
                status='generating',
                expires_at=timezone.now() + timedelta(days=7)
            )
            
            return Response({
                'report_id': report.id,
                'status': 'generating'
            }, status=status.HTTP_202_ACCEPTED)


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """Report template management"""
    serializer_class = ReportTemplateSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return ReportTemplate.objects.filter(teacher=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)
