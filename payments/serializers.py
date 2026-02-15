"""
Payment Serializers
"""
from rest_framework import serializers
from decimal import Decimal
from .models import Payment, PaymentTransaction, PaymentPlan, PaymentReminder, PaymentMethod


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Payment transaction serializer"""
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'amount', 'payment_method', 'transaction_date',
            'transaction_reference', 'receipt_number', 'notes',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PaymentSerializer(serializers.ModelSerializer):
    """Main payment serializer"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_code = serializers.CharField(source='student.code', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    days_overdue = serializers.SerializerMethodField()
    transactions = PaymentTransactionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'student', 'student_name', 'student_code', 'group', 'group_name',
            'payment_type', 'amount', 'amount_paid', 'remaining_amount',
            'payment_method', 'status', 'due_date', 'payment_date',
            'period_start', 'period_end', 'reference_number',
            'transaction_id', 'discount_amount', 'discount_reason',
            'notes', 'internal_notes', 'is_overdue', 'days_overdue',
            'transactions', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'remaining_amount', 'reference_number', 'is_overdue',
            'days_overdue', 'created_at', 'updated_at'
        ]
    
    def get_is_overdue(self, obj):
        return obj.is_overdue()
    
    def get_days_overdue(self, obj):
        return obj.days_overdue()


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payments"""
    
    class Meta:
        model = Payment
        fields = [
            'student', 'group', 'payment_type', 'amount', 'payment_method',
            'due_date', 'period_start', 'period_end', 'notes'
        ]
    
    def validate(self, data):
        # Ensure teacher owns the student
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            student = data.get('student')
            if student and student.teacher != request.user:
                raise serializers.ValidationError("You can only create payments for your own students")
        
        # Validate amount
        amount = data.get('amount')
        if amount and amount <= 0:
            raise serializers.ValidationError("Payment amount must be positive")
        
        # Validate period for monthly payments
        payment_type = data.get('payment_type')
        if payment_type == 'monthly':
            if not data.get('period_start') or not data.get('period_end'):
                raise serializers.ValidationError("Period start and end dates are required for monthly payments")
        
        return data
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return Payment.objects.create(**validated_data)


class PaymentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating payments"""
    
    class Meta:
        model = Payment
        fields = [
            'amount_paid', 'payment_method', 'payment_date',
            'transaction_id', 'notes', 'status'
        ]
    
    def validate_amount_paid(self, value):
        if value < 0:
            raise serializers.ValidationError("Amount paid cannot be negative")
        
        # Check if amount paid doesn't exceed total amount
        if self.instance and value > self.instance.amount:
            raise serializers.ValidationError("Amount paid cannot exceed total amount")
        
        return value


class AddPaymentSerializer(serializers.Serializer):
    """Serializer for adding payment amounts"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    payment_method = serializers.ChoiceField(choices=Payment.PAYMENT_METHODS, default='cash')
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    transaction_reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    def validate_amount(self, value):
        # Validate against payment instance if available
        payment = self.context.get('payment')
        if payment:
            if payment.amount_paid + value > payment.amount:
                raise serializers.ValidationError("Payment amount exceeds remaining balance")
        return value


class PaymentPlanSerializer(serializers.ModelSerializer):
    """Payment plan serializer"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentPlan
        fields = [
            'id', 'student', 'student_name', 'total_amount',
            'installment_amount', 'number_of_installments',
            'start_date', 'installment_frequency', 'status',
            'installments_paid', 'amount_paid', 'progress_percentage',
            'description', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'installments_paid', 'amount_paid', 'progress_percentage',
            'created_at', 'updated_at'
        ]
    
    def get_progress_percentage(self, obj):
        if obj.number_of_installments > 0:
            return round((obj.installments_paid / obj.number_of_installments) * 100, 2)
        return 0
    
    def validate(self, data):
        # Ensure teacher owns the student
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            student = data.get('student')
            if student and student.teacher != request.user:
                raise serializers.ValidationError("You can only create payment plans for your own students")
        
        # Validate amounts
        total_amount = data.get('total_amount')
        installment_amount = data.get('installment_amount')
        number_of_installments = data.get('number_of_installments')
        
        if total_amount and installment_amount and number_of_installments:
            expected_total = installment_amount * number_of_installments
            if abs(expected_total - total_amount) > Decimal('0.01'):
                raise serializers.ValidationError(
                    "Total amount should equal installment amount × number of installments"
                )
        
        return data
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return PaymentPlan.objects.create(**validated_data)


class PaymentReminderSerializer(serializers.ModelSerializer):
    """Payment reminder serializer"""
    student_name = serializers.CharField(source='payment.student.name', read_only=True)
    payment_amount = serializers.DecimalField(source='payment.amount', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = PaymentReminder
        fields = [
            'id', 'payment', 'student_name', 'payment_amount',
            'reminder_type', 'reminder_date', 'title', 'message',
            'is_sent', 'sent_at', 'created_at'
        ]
        read_only_fields = ['id', 'is_sent', 'sent_at', 'created_at']


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Payment method serializer"""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'name', 'method_type', 'account_details',
            'instructions', 'is_active', 'is_default',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return PaymentMethod.objects.create(**validated_data)


class PaymentSummarySerializer(serializers.Serializer):
    """Payment summary serializer"""
    total_payments = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_pending = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_overdue = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_count = serializers.IntegerField()
    overdue_count = serializers.IntegerField()
    paid_count = serializers.IntegerField()


class BulkPaymentSerializer(serializers.Serializer):
    """Serializer for bulk payment operations"""
    payment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    action = serializers.ChoiceField(choices=[
        ('mark_paid', 'Mark as Paid'),
        ('send_reminder', 'Send Reminder'),
        ('apply_discount', 'Apply Discount'),
    ])
    
    # Optional fields based on action
    payment_method = serializers.ChoiceField(
        choices=Payment.PAYMENT_METHODS,
        required=False
    )
    discount_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False
    )
    discount_reason = serializers.CharField(
        max_length=200,
        required=False
    )
    notes = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True
    )
    
    def validate(self, data):
        action = data.get('action')
        
        if action == 'mark_paid' and not data.get('payment_method'):
            raise serializers.ValidationError("Payment method is required for mark_paid action")
        
        if action == 'apply_discount':
            if not data.get('discount_amount'):
                raise serializers.ValidationError("Discount amount is required for apply_discount action")
            if data.get('discount_amount') <= 0:
                raise serializers.ValidationError("Discount amount must be positive")
        
        return data