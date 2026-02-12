"""
Receipt Models
Receipt generation and management system
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class Receipt(models.Model):
    """
    Core Receipt model
    """
    RECEIPT_STATUS = [
        ('pending', 'Pending Generation'),
        ('generated', 'Generated'),
        ('sent', 'Sent'),
        ('failed', 'Generation Failed'),
    ]
    
    RECEIPT_TYPES = [
        ('payment', 'Payment Receipt'),
        ('monthly', 'Monthly Receipt'),
        ('refund', 'Refund Receipt'),
        ('adjustment', 'Adjustment Receipt'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField('payments.Payment', on_delete=models.CASCADE, related_name='receipt')
    
    # Receipt Details
    receipt_number = models.CharField(max_length=50, unique=True)
    receipt_type = models.CharField(max_length=20, choices=RECEIPT_TYPES, default='payment')
    status = models.CharField(max_length=20, choices=RECEIPT_STATUS, default='pending')
    
    # Content
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # PDF Generation
    pdf_file = models.FileField(upload_to='receipts/', blank=True, null=True)
    pdf_generated_at = models.DateTimeField(blank=True, null=True)
    
    # Sending
    sent_at = models.DateTimeField(blank=True, null=True)
    sent_to = models.EmailField(blank=True, null=True)
    sent_via_whatsapp = models.BooleanField(default=False)
    
    # Error Handling
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'receipts'
        indexes = [
            models.Index(fields=['receipt_number']),
            models.Index(fields=['payment', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.payment.student.name}"
    
    def save(self, *args, **kwargs):
        # Generate receipt number if not provided
        if not self.receipt_number:
            self.receipt_number = self.generate_receipt_number()
        
        # Set title if not provided
        if not self.title:
            self.title = f"Payment Receipt - {self.payment.student.name}"
        
        super().save(*args, **kwargs)
    
    def generate_receipt_number(self):
        """Generate unique receipt number"""
        import random
        import string
        
        prefix = 'RCP'
        timestamp = timezone.now().strftime('%Y%m%d')
        random_suffix = ''.join(random.choices(string.digits, k=4))
        
        # Ensure uniqueness
        while True:
            receipt_number = f"{prefix}-{timestamp}-{random_suffix}"
            if not Receipt.objects.filter(receipt_number=receipt_number).exists():
                return receipt_number
            random_suffix = ''.join(random.choices(string.digits, k=4))
    
    def generate_pdf(self):
        """Generate PDF receipt"""
        try:
            from .utils import generate_receipt_pdf
            
            pdf_content = generate_receipt_pdf(self)
            
            # Save PDF file
            from django.core.files.base import ContentFile
            pdf_file = ContentFile(pdf_content)
            self.pdf_file.save(
                f"receipt_{self.receipt_number}.pdf",
                pdf_file,
                save=False
            )
            
            self.status = 'generated'
            self.pdf_generated_at = timezone.now()
            self.error_message = None
            self.save()
            
            return True
            
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
            self.retry_count += 1
            self.save()
            return False
    
    def send_receipt(self, email=None, via_whatsapp=False):
        """Send receipt via email or WhatsApp"""
        if self.status != 'generated' or not self.pdf_file:
            return False
        
        try:
            if email:
                from .utils import send_receipt_email
                send_receipt_email(self, email)
                self.sent_to = email
            
            if via_whatsapp:
                from .utils import send_receipt_whatsapp
                send_receipt_whatsapp(self)
                self.sent_via_whatsapp = True
            
            self.status = 'sent'
            self.sent_at = timezone.now()
            self.save()
            
            return True
            
        except Exception as e:
            self.error_message = str(e)
            self.save()
            return False
    
    def retry_generation(self):
        """Retry PDF generation"""
        if self.retry_count < 3:
            return self.generate_pdf()
        return False


class ReceiptTemplate(models.Model):
    """
    Receipt templates for customization
    """
    TEMPLATE_TYPES = [
        ('payment', 'Payment Receipt'),
        ('monthly', 'Monthly Receipt'),
        ('refund', 'Refund Receipt'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='receipt_templates'
    )
    
    # Template Details
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    
    # Design Settings
    header_text = models.CharField(max_length=200, blank=True, null=True)
    footer_text = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='receipt_logos/', blank=True, null=True)
    
    # Layout Settings
    include_student_details = models.BooleanField(default=True)
    include_payment_breakdown = models.BooleanField(default=True)
    include_signature = models.BooleanField(default=True)
    
    # Colors (hex codes)
    primary_color = models.CharField(max_length=7, default='#000000')
    secondary_color = models.CharField(max_length=7, default='#666666')
    
    # Language
    language = models.CharField(max_length=5, choices=[
        ('ar', 'Arabic'),
        ('en', 'English'),
    ], default='ar')
    
    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'receipt_templates'
        indexes = [
            models.Index(fields=['teacher', 'template_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.teacher.username} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default template per type per teacher
        if self.is_default:
            ReceiptTemplate.objects.filter(
                teacher=self.teacher,
                template_type=self.template_type,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        
        super().save(*args, **kwargs)


class ReceiptItem(models.Model):
    """
    Individual items in a receipt (for detailed breakdowns)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='items')
    
    # Item Details
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Dates (for period-based items)
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'receipt_items'
        indexes = [
            models.Index(fields=['receipt']),
        ]
    
    def __str__(self):
        return f"{self.receipt.receipt_number} - {self.description}"
    
    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class ReceiptLog(models.Model):
    """
    Log of receipt operations
    """
    ACTION_TYPES = [
        ('generated', 'PDF Generated'),
        ('sent_email', 'Sent via Email'),
        ('sent_whatsapp', 'Sent via WhatsApp'),
        ('failed', 'Generation Failed'),
        ('retry', 'Retry Attempted'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='logs')
    
    # Action Details
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    details = models.TextField(blank=True, null=True)
    
    # Result
    success = models.BooleanField()
    error_message = models.TextField(blank=True, null=True)
    
    # System Fields
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'receipt_logs'
        indexes = [
            models.Index(fields=['receipt', 'action']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.receipt.receipt_number} - {self.action}"


class ReceiptBatch(models.Model):
    """
    Batch processing for multiple receipts
    """
    BATCH_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='receipt_batches'
    )
    
    # Batch Details
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=BATCH_STATUS, default='pending')
    
    # Processing
    total_receipts = models.PositiveIntegerField(default=0)
    processed_receipts = models.PositiveIntegerField(default=0)
    failed_receipts = models.PositiveIntegerField(default=0)
    
    # Timing
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'receipt_batches'
        indexes = [
            models.Index(fields=['teacher', 'status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.teacher.username} - {self.name}"
    
    def add_receipt(self, receipt):
        """Add receipt to batch"""
        ReceiptBatchItem.objects.create(
            batch=self,
            receipt=receipt
        )
        self.total_receipts += 1
        self.save(update_fields=['total_receipts'])
    
    def process_batch(self):
        """Process all receipts in batch"""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.save()
        
        batch_items = self.batch_items.all()
        
        for item in batch_items:
            try:
                if item.receipt.generate_pdf():
                    self.processed_receipts += 1
                    item.status = 'completed'
                else:
                    self.failed_receipts += 1
                    item.status = 'failed'
                item.save()
                
            except Exception as e:
                self.failed_receipts += 1
                item.status = 'failed'
                item.error_message = str(e)
                item.save()
        
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()


class ReceiptBatchItem(models.Model):
    """
    Individual receipt in a batch
    """
    ITEM_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(ReceiptBatch, on_delete=models.CASCADE, related_name='batch_items')
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE)
    
    # Status
    status = models.CharField(max_length=20, choices=ITEM_STATUS, default='pending')
    error_message = models.TextField(blank=True, null=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'receipt_batch_items'
        unique_together = ['batch', 'receipt']
        indexes = [
            models.Index(fields=['batch', 'status']),
        ]
    
    def __str__(self):
        return f"{self.batch.name} - {self.receipt.receipt_number}"