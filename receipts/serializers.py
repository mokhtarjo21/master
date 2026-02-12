"""
Receipt Serializers
"""
from rest_framework import serializers
from .models import Receipt, ReceiptTemplate, ReceiptItem, ReceiptLog, ReceiptBatch


class ReceiptItemSerializer(serializers.ModelSerializer):
    """Receipt item serializer"""
    
    class Meta:
        model = ReceiptItem
        fields = [
            'id', 'description', 'quantity', 'unit_price', 'total_price',
            'period_start', 'period_end', 'created_at'
        ]
        read_only_fields = ['id', 'total_price', 'created_at']


class ReceiptLogSerializer(serializers.ModelSerializer):
    """Receipt log serializer"""
    
    class Meta:
        model = ReceiptLog
        fields = [
            'id', 'action', 'details', 'success', 'error_message',
            'performed_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ReceiptSerializer(serializers.ModelSerializer):
    """Main receipt serializer"""
    student_name = serializers.CharField(source='payment.student.name', read_only=True)
    student_code = serializers.CharField(source='payment.student.code', read_only=True)
    payment_amount = serializers.DecimalField(source='payment.amount', max_digits=10, decimal_places=2, read_only=True)
    payment_type = serializers.CharField(source='payment.get_payment_type_display', read_only=True)
    pdf_url = serializers.SerializerMethodField()
    items = ReceiptItemSerializer(many=True, read_only=True)
    logs = ReceiptLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'payment', 'student_name', 'student_code',
            'receipt_number', 'receipt_type', 'status', 'title',
            'description', 'payment_amount', 'payment_type',
            'pdf_file', 'pdf_url', 'pdf_generated_at', 'sent_at',
            'sent_to', 'sent_via_whatsapp', 'error_message',
            'retry_count', 'items', 'logs', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'receipt_number', 'pdf_generated_at', 'sent_at',
            'error_message', 'retry_count', 'created_at', 'updated_at'
        ]
    
    def get_pdf_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
        return None


class ReceiptCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating receipts"""
    
    class Meta:
        model = Receipt
        fields = [
            'payment', 'receipt_type', 'title', 'description'
        ]
    
    def validate_payment(self, value):
        # Ensure teacher owns the payment
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if value.student.teacher != request.user:
                raise serializers.ValidationError("You can only create receipts for your own payments")
        
        # Check if receipt already exists
        if hasattr(value, 'receipt'):
            raise serializers.ValidationError("Receipt already exists for this payment")
        
        return value


class ReceiptTemplateSerializer(serializers.ModelSerializer):
    """Receipt template serializer"""
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ReceiptTemplate
        fields = [
            'id', 'name', 'template_type', 'header_text', 'footer_text',
            'logo', 'logo_url', 'include_student_details',
            'include_payment_breakdown', 'include_signature',
            'primary_color', 'secondary_color', 'language',
            'is_active', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at']
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
        return None
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return ReceiptTemplate.objects.create(**validated_data)


class ReceiptBatchSerializer(serializers.ModelSerializer):
    """Receipt batch serializer"""
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = ReceiptBatch
        fields = [
            'id', 'name', 'description', 'status', 'total_receipts',
            'processed_receipts', 'failed_receipts', 'progress_percentage',
            'started_at', 'completed_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'teacher', 'status', 'total_receipts', 'processed_receipts',
            'failed_receipts', 'progress_percentage', 'started_at',
            'completed_at', 'created_at'
        ]
    
    def get_progress_percentage(self, obj):
        if obj.total_receipts > 0:
            return round(((obj.processed_receipts + obj.failed_receipts) / obj.total_receipts) * 100, 2)
        return 0
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return ReceiptBatch.objects.create(**validated_data)


class BulkReceiptGenerationSerializer(serializers.Serializer):
    """Serializer for bulk receipt generation"""
    payment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    receipt_type = serializers.ChoiceField(
        choices=Receipt.RECEIPT_TYPES,
        default='payment'
    )
    auto_generate_pdf = serializers.BooleanField(default=True)
    
    def validate_payment_ids(self, value):
        from payments.models import Payment
        
        # Ensure teacher owns all payments
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            payments = Payment.objects.filter(
                id__in=value,
                student__teacher=request.user
            )
            
            if payments.count() != len(value):
                raise serializers.ValidationError("Some payments not found or not owned by you")
            
            # Check for existing receipts
            existing_receipts = payments.filter(receipt__isnull=False).count()
            if existing_receipts > 0:
                raise serializers.ValidationError(f"{existing_receipts} payments already have receipts")
        
        return value


class ReceiptSendSerializer(serializers.Serializer):
    """Serializer for sending receipts"""
    email = serializers.EmailField(required=False)
    via_whatsapp = serializers.BooleanField(default=False)
    
    def validate(self, data):
        if not data.get('email') and not data.get('via_whatsapp'):
            raise serializers.ValidationError("Either email or via_whatsapp must be specified")
        return data


class MonthlyReceiptGenerationSerializer(serializers.Serializer):
    """Serializer for monthly receipt generation"""
    year = serializers.IntegerField(min_value=2020, max_value=2030)
    month = serializers.IntegerField(min_value=1, max_value=12)
    auto_generate_pdf = serializers.BooleanField(default=True)
    auto_send_email = serializers.BooleanField(default=False)