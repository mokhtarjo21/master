"""
Payment Views
"""
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import date, timedelta
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal

from accounts.permissions import IsTeacher, ReadOnlyForStudentsAndParents
from .models import Payment, PaymentTransaction, PaymentPlan, PaymentReminder, PaymentMethod
from .serializers import (
    PaymentSerializer, PaymentCreateSerializer, PaymentUpdateSerializer,
    AddPaymentSerializer, PaymentPlanSerializer, PaymentReminderSerializer,
    PaymentMethodSerializer, PaymentSummarySerializer, BulkPaymentSerializer,
    PaymentTransactionSerializer
)


class PaymentViewSet(viewsets.ModelViewSet):
    """Payment management viewset"""
    permission_classes = [ReadOnlyForStudentsAndParents]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_type', 'payment_method', 'student', 'group']
    search_fields = ['student__name', 'student__code', 'reference_number']
    ordering_fields = ['due_date', 'amount', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        if self.request.user.user_type == 'teacher':
            return Payment.objects.filter(
                student__teacher=self.request.user,
                is_active=True
            ).select_related('student')
        elif self.request.user.user_type == 'student':
            return Payment.objects.filter(
                student__user=self.request.user,
                is_active=True
            ).select_related('student')
        elif self.request.user.user_type == 'parent':
            from students.models import StudentParentLink
            linked_student_ids = StudentParentLink.objects.filter(
                parent__user=self.request.user,
                is_active=True,
                can_view_payments=True
            ).values_list('student_id', flat=True)
            
            return Payment.objects.filter(
                student_id__in=linked_student_ids,
                is_active=True
            ).select_related('student')
        
        return Payment.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PaymentUpdateSerializer
        return PaymentSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new payment"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can create payments'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            payment = serializer.save()
            response_serializer = PaymentSerializer(payment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_payment(self, request, pk=None):
        """Add payment amount to existing payment"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can add payments'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        payment = self.get_object()
        serializer = AddPaymentSerializer(
            data=request.data,
            context={'payment': payment, 'request': request}
        )
        
        if serializer.is_valid():
            amount = serializer.validated_data['amount']
            payment_method = serializer.validated_data['payment_method']
            notes = serializer.validated_data.get('notes', '')
            transaction_reference = serializer.validated_data.get('transaction_reference', '')
            
            try:
                payment.add_payment(amount, payment_method, notes)
                
                # Update transaction reference if provided
                if transaction_reference:
                    latest_transaction = payment.transactions.latest('created_at')
                    latest_transaction.transaction_reference = transaction_reference
                    latest_transaction.save()
                
                response_serializer = PaymentSerializer(payment)
                return Response(response_serializer.data)
                
            except ValueError as e:
                return Response(
                    {'error': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def apply_discount(self, request, pk=None):
        """Apply discount to payment"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can apply discounts'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        payment = self.get_object()
        discount_amount = request.data.get('discount_amount')
        reason = request.data.get('reason', '')
        
        if not discount_amount:
            return Response(
                {'error': 'discount_amount is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            discount_amount = Decimal(str(discount_amount))
            payment.apply_discount(discount_amount, reason)
            
            response_serializer = PaymentSerializer(payment)
            return Response(response_serializer.data)
            
        except (ValueError, TypeError) as e:
            return Response(
                {'error': f'Invalid discount amount: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue payments"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can view overdue payments'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset().filter(
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'partial']
        )
        
        serializer = PaymentSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def due_soon(self, request):
        """Get payments due soon"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can view due payments'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        days = int(request.query_params.get('days', 7))
        due_date = timezone.now().date() + timedelta(days=days)
        
        queryset = self.get_queryset().filter(
            due_date__lte=due_date,
            status__in=['pending', 'partial']
        )
        
        serializer = PaymentSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get payment summary statistics"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can view payment summary'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        
        # Apply date filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        # Calculate summary
        summary = queryset.aggregate(
            total_payments=Count('id'),
            total_amount=Sum('amount'),
            total_paid=Sum('amount_paid'),
            pending_count=Count('id', filter=Q(status='pending')),
            overdue_count=Count('id', filter=Q(status='overdue')),
            paid_count=Count('id', filter=Q(status='paid'))
        )
        
        # Calculate pending and overdue amounts
        pending_amount = queryset.filter(status__in=['pending', 'partial']).aggregate(
            total=Sum('remaining_amount')
        )['total'] or Decimal('0')
        
        overdue_amount = queryset.filter(status='overdue').aggregate(
            total=Sum('remaining_amount')
        )['total'] or Decimal('0')
        
        summary.update({
            'total_pending': pending_amount,
            'total_overdue': overdue_amount
        })
        
        # Handle None values
        for key, value in summary.items():
            if value is None:
                summary[key] = 0
        
        serializer = PaymentSummarySerializer(summary)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk actions on payments"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can perform bulk actions'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BulkPaymentSerializer(data=request.data)
        if serializer.is_valid():
            payment_ids = serializer.validated_data['payment_ids']
            action = serializer.validated_data['action']
            
            # Get payments owned by teacher
            payments = self.get_queryset().filter(id__in=payment_ids)
            
            if not payments.exists():
                return Response(
                    {'error': 'No valid payments found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            results = {'processed': 0, 'errors': []}
            
            if action == 'mark_paid':
                payment_method = serializer.validated_data['payment_method']
                notes = serializer.validated_data.get('notes', 'Bulk payment')
                
                for payment in payments:
                    if payment.status in ['pending', 'partial']:
                        try:
                            remaining = payment.remaining_amount
                            payment.add_payment(remaining, payment_method, notes)
                            results['processed'] += 1
                        except Exception as e:
                            results['errors'].append(f"Payment {payment.id}: {str(e)}")
            
            elif action == 'apply_discount':
                discount_amount = serializer.validated_data['discount_amount']
                discount_reason = serializer.validated_data.get('discount_reason', 'Bulk discount')
                
                for payment in payments:
                    try:
                        payment.apply_discount(discount_amount, discount_reason)
                        results['processed'] += 1
                    except Exception as e:
                        results['errors'].append(f"Payment {payment.id}: {str(e)}")
            
            elif action == 'send_reminder':
                # Create payment reminders
                for payment in payments:
                    if payment.status in ['pending', 'partial', 'overdue']:
                        PaymentReminder.objects.create(
                            payment=payment,
                            reminder_type='overdue' if payment.is_overdue() else 'due_soon',
                            reminder_date=timezone.now().date(),
                            title=f"Payment Reminder - {payment.student.name}",
                            message=f"Payment of {payment.remaining_amount} is due."
                        )
                        results['processed'] += 1
            
            return Response(results)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def monthly_report(self, request):
        """Get monthly payment report"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can view reports'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))
        
        # Get payments for the month
        queryset = self.get_queryset().filter(
            payment_date__year=year,
            payment_date__month=month,
            status='paid'
        )
        
        # Group by payment type
        report_data = {}
        for payment_type, _ in Payment.PAYMENT_TYPES:
            type_payments = queryset.filter(payment_type=payment_type)
            report_data[payment_type] = {
                'count': type_payments.count(),
                'total_amount': type_payments.aggregate(
                    total=Sum('amount_paid')
                )['total'] or Decimal('0')
            }
        
        # Overall totals
        report_data['totals'] = {
            'total_payments': queryset.count(),
            'total_amount': queryset.aggregate(
                total=Sum('amount_paid')
            )['total'] or Decimal('0')
        }
        
        return Response(report_data)
    
    @action(detail=False, methods=['post'])
    def generate_monthly_payments(self, request):
        """Auto-generate monthly payments for all students"""
        if request.user.user_type != 'teacher':
            return Response(
                {'error': 'Only teachers can generate payments'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .utils import sync_monthly_payments_for_teacher
        
        month = request.data.get('month')
        year = request.data.get('year')
        
        # Use current month/year if not provided
        if not month or not year:
            today = timezone.now().date()
            month = month or today.month
            year = year or today.year
        
        try:
            stats = sync_monthly_payments_for_teacher(
                teacher=request.user,
                month=int(month),
                year=int(year)
            )
            
            return Response({
                'message': 'Monthly payments generated successfully',
                'stats': stats,
                'period': f'{year}-{month:02d}'
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to generate payments: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentPlanViewSet(viewsets.ModelViewSet):
    """Payment plan management"""
    serializer_class = PaymentPlanSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'student']
    ordering_fields = ['start_date', 'total_amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return PaymentPlan.objects.filter(
            student__teacher=self.request.user
        ).select_related('student')
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update payment plan progress"""
        plan = self.get_object()
        plan.update_progress()
        
        serializer = PaymentPlanSerializer(plan)
        return Response(serializer.data)


class PaymentReminderViewSet(viewsets.ModelViewSet):
    """Payment reminder management"""
    serializer_class = PaymentReminderSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['reminder_type', 'is_sent']
    ordering_fields = ['reminder_date', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return PaymentReminder.objects.filter(
            payment__student__teacher=self.request.user
        ).select_related('payment', 'payment__student')
    
    @action(detail=True, methods=['post'])
    def mark_sent(self, request, pk=None):
        """Mark reminder as sent"""
        reminder = self.get_object()
        reminder.is_sent = True
        reminder.sent_at = timezone.now()
        reminder.save()
        
        serializer = PaymentReminderSerializer(reminder)
        return Response(serializer.data)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """Payment method management"""
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return PaymentMethod.objects.filter(teacher=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set payment method as default"""
        method = self.get_object()
        method.is_default = True
        method.save()
        
        serializer = PaymentMethodSerializer(method)
        return Response(serializer.data)


class PaymentTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """Payment transaction read-only viewset"""
    serializer_class = PaymentTransactionSerializer
    permission_classes = [ReadOnlyForStudentsAndParents]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['payment_method', 'transaction_date']
    ordering_fields = ['transaction_date', 'amount']
    ordering = ['-transaction_date']
    
    def get_queryset(self):
        if self.request.user.user_type == 'teacher':
            return PaymentTransaction.objects.filter(
                payment__student__teacher=self.request.user
            ).select_related('payment', 'payment__student')
        elif self.request.user.user_type == 'student':
            return PaymentTransaction.objects.filter(
                payment__student__user=self.request.user
            ).select_related('payment')
        elif self.request.user.user_type == 'parent':
            from students.models import StudentParentLink
            linked_student_ids = StudentParentLink.objects.filter(
                parent__user=self.request.user,
                is_active=True,
                can_view_payments=True
            ).values_list('student_id', flat=True)
            
            return PaymentTransaction.objects.filter(
                payment__student_id__in=linked_student_ids
            ).select_related('payment', 'payment__student')
        
        return PaymentTransaction.objects.none()