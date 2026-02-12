"""
Receipt Views
"""
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from django.utils import timezone
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsTeacher, ReadOnlyForStudentsAndParents
from .models import Receipt, ReceiptTemplate, ReceiptBatch
from .serializers import (
    ReceiptSerializer, ReceiptCreateSerializer, ReceiptTemplateSerializer,
    ReceiptBatchSerializer, BulkReceiptGenerationSerializer,
    ReceiptSendSerializer, MonthlyReceiptGenerationSerializer
)
from .utils import generate_monthly_receipts, bulk_generate_pdfs, create_receipt_from_payment


class ReceiptViewSet(viewsets.ModelViewSet):
    """Receipt management viewset"""
    permission_classes = [ReadOnlyForStudentsAndParents]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'receipt_type', 'payment__student']
    search_fields = ['receipt_number', 'payment__student__name', 'title']
    ordering_fields = ['created_at', 'pdf_generated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        if self.request.user.user_type == 'teacher':
            return Receipt.objects.filter(
                payment__student__teacher=self.request.user
            ).select_related('payment', 'payment__student')
        elif self.request.user.user_type == 'student':
            return Receipt.objects.filter(
                payment__student__user=self.request.user
            ).select_related('payment')
        elif self.request.user.user_type == 'parent':
            from students.models import StudentParentLink
            linked_student_ids = StudentParentLink.objects.filter(
                parent__user=self.request.user,
                is_active=True,
                can_view_payments=True
            ).values_list('student_id', flat=True)
            
            return Receipt.objects.filter(
                payment__student_id__in=linked_student_ids
            ).select_related('payment', 'payment__student')
        
        return Receipt.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReceiptCreateSerializer
        return ReceiptSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new receipt"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can create receipts'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            receipt = serializer.save()
            response_serializer = ReceiptSerializer(receipt)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def generate_pdf(self, request, pk=None):
        """Generate PDF for receipt"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can generate PDFs'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        receipt = self.get_object()
        
        if receipt.generate_pdf():
            serializer = ReceiptSerializer(receipt)
            return Response(serializer.data)
        else:
            return Response(
                {'error': f'PDF generation failed: {receipt.error_message}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def retry_generation(self, request, pk=None):
        """Retry PDF generation"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can retry generation'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        receipt = self.get_object()
        
        if receipt.retry_generation():
            serializer = ReceiptSerializer(receipt)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Maximum retry attempts reached'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def send_receipt(self, request, pk=None):
        """Send receipt via email or WhatsApp"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can send receipts'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        receipt = self.get_object()
        serializer = ReceiptSendSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            via_whatsapp = serializer.validated_data.get('via_whatsapp', False)
            
            if receipt.send_receipt(email=email, via_whatsapp=via_whatsapp):
                response_serializer = ReceiptSerializer(receipt)
                return Response(response_serializer.data)
            else:
                return Response(
                    {'error': f'Failed to send receipt: {receipt.error_message}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """Download receipt PDF"""
        receipt = self.get_object()
        
        if not receipt.pdf_file:
            return Response(
                {'error': 'PDF not generated yet'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        response = HttpResponse(
            receipt.pdf_file.read(),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="receipt_{receipt.receipt_number}.pdf"'
        return response
    
    @action(detail=False, methods=['post'])
    def bulk_generate(self, request):
        """Bulk generate receipts"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can bulk generate receipts'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BulkReceiptGenerationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            payment_ids = serializer.validated_data['payment_ids']
            receipt_type = serializer.validated_data['receipt_type']
            auto_generate_pdf = serializer.validated_data['auto_generate_pdf']
            
            from payments.models import Payment
            payments = Payment.objects.filter(
                id__in=payment_ids,
                student__teacher=request.user
            )
            
            receipts_created = []
            for payment in payments:
                receipt = Receipt.objects.create(
                    payment=payment,
                    receipt_type=receipt_type,
                    title=f"{receipt_type.title()} Receipt - {payment.student.name}"
                )
                receipts_created.append(receipt)
            
            # Auto-generate PDFs if requested
            if auto_generate_pdf:
                pdf_results = bulk_generate_pdfs(receipts_created)
                return Response({
                    'message': f'Created {len(receipts_created)} receipts',
                    'receipts_created': len(receipts_created),
                    'pdf_generation': pdf_results
                })
            
            return Response({
                'message': f'Created {len(receipts_created)} receipts',
                'receipts_created': len(receipts_created)
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def generate_monthly(self, request):
        """Generate monthly receipts"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can generate monthly receipts'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MonthlyReceiptGenerationSerializer(data=request.data)
        if serializer.is_valid():
            year = serializer.validated_data['year']
            month = serializer.validated_data['month']
            auto_generate_pdf = serializer.validated_data['auto_generate_pdf']
            
            receipts = generate_monthly_receipts(request.user, year, month)
            
            if auto_generate_pdf and receipts:
                pdf_results = bulk_generate_pdfs(receipts)
                return Response({
                    'message': f'Generated {len(receipts)} monthly receipts',
                    'receipts_created': len(receipts),
                    'pdf_generation': pdf_results
                })
            
            return Response({
                'message': f'Generated {len(receipts)} monthly receipts',
                'receipts_created': len(receipts)
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get receipts pending PDF generation"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can view pending receipts'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset().filter(status='pending')
        serializer = ReceiptSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def failed(self, request):
        """Get receipts with failed PDF generation"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can view failed receipts'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset().filter(status='failed')
        serializer = ReceiptSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get receipt statistics"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can view statistics'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        
        stats = queryset.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            generated=Count('id', filter=Q(status='generated')),
            sent=Count('id', filter=Q(status='sent')),
            failed=Count('id', filter=Q(status='failed'))
        )
        
        return Response(stats)


class ReceiptTemplateViewSet(viewsets.ModelViewSet):
    """Receipt template management"""
    serializer_class = ReceiptTemplateSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['template_type', 'is_active', 'is_default']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        return ReceiptTemplate.objects.filter(teacher=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set template as default"""
        template = self.get_object()
        template.is_default = True
        template.save()
        
        serializer = ReceiptTemplateSerializer(template)
        return Response(serializer.data)


class ReceiptBatchViewSet(viewsets.ModelViewSet):
    """Receipt batch management"""
    serializer_class = ReceiptBatchSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'started_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return ReceiptBatch.objects.filter(teacher=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_receipt(self, request, pk=None):
        """Add receipt to batch"""
        batch = self.get_object()
        receipt_id = request.data.get('receipt_id')
        
        if not receipt_id:
            return Response(
                {'error': 'receipt_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            receipt = Receipt.objects.get(
                id=receipt_id,
                payment__student__teacher=request.user
            )
            batch.add_receipt(receipt)
            
            serializer = ReceiptBatchSerializer(batch)
            return Response(serializer.data)
            
        except Receipt.DoesNotExist:
            return Response(
                {'error': 'Receipt not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process batch"""
        batch = self.get_object()
        
        if batch.status != 'pending':
            return Response(
                {'error': 'Batch is not in pending status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process batch in background (in a real app, use Celery)
        batch.process_batch()
        
        serializer = ReceiptBatchSerializer(batch)
        return Response(serializer.data)