"""
Notification Models
Multi-channel notification system with WhatsApp integration
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class Notification(models.Model):
    """
    Core Notification model
    """
    RECIPIENT_TYPES = [
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('teacher', 'Teacher'),
        ('group', 'Group'),
        ('all_students', 'All Students'),
    ]
    
    NOTIFICATION_TYPES = [
        ('payment', 'Payment'),
        ('session', 'Session'),
        ('attendance', 'Attendance'),
        ('grade', 'Grade'),
        ('announcement', 'Announcement'),
        ('reminder', 'Reminder'),
        ('alert', 'Alert'),
        ('receipt', 'Receipt'),
        ('system', 'System'),
    ]
    
    CHANNELS = [
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('push', 'Push Notification'),
        ('sms', 'SMS'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_notifications'
    )
    
    # Recipient Information
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPES)
    recipient_id = models.UUIDField(blank=True, null=True)  # Specific recipient ID
    recipient_name = models.CharField(max_length=200, blank=True, null=True)
    recipient_phone = models.CharField(max_length=20, blank=True, null=True)
    recipient_email = models.EmailField(blank=True, null=True)
    
    # Notification Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    
    # Channel & Delivery
    channel = models.CharField(max_length=20, choices=CHANNELS, default='whatsapp')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Scheduling
    scheduled_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(blank=True, null=True)
    
    # Error Handling
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    
    # Additional Data
    metadata = models.JSONField(default=dict)  # Store additional context
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['teacher', 'status']),
            models.Index(fields=['recipient_type', 'recipient_id']),
            models.Index(fields=['scheduled_at', 'status']),
            models.Index(fields=['notification_type', 'channel']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.recipient_name} ({self.channel})"
    
    def send(self):
        """Send notification via specified channel"""
        try:
            if self.channel == 'whatsapp':
                return self._send_whatsapp()
            elif self.channel == 'email':
                return self._send_email()
            elif self.channel == 'push':
                return self._send_push()
            elif self.channel == 'sms':
                return self._send_sms()
            else:
                raise ValueError(f"Unsupported channel: {self.channel}")
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
            self.retry_count += 1
            self.save()
            return False
    
    def _send_whatsapp(self):
        """Send WhatsApp message"""
        if not self.recipient_phone:
            raise ValueError("No phone number provided for WhatsApp")
        
        # Format phone number
        phone = self.recipient_phone.replace('+', '').replace(' ', '').replace('-', '')
        if not phone.startswith('966'):
            phone = '966' + phone.lstrip('0')
        
        # Create WhatsApp payload
        whatsapp_data = {
            'phone': phone,
            'message': f"*{self.title}*\n\n{self.message}",
            'type': self.notification_type,
            'metadata': self.metadata
        }
        
        # TODO: Integrate with actual WhatsApp API
        # For now, we'll simulate success
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
        
        # Log the WhatsApp payload for debugging
        NotificationLog.objects.create(
            notification=self,
            action='whatsapp_sent',
            details=f"WhatsApp message sent to {phone}",
            payload=whatsapp_data
        )
        
        return True
    
    def _send_email(self):
        """Send email notification"""
        if not self.recipient_email:
            raise ValueError("No email address provided")
        
        from django.core.mail import send_mail
        
        send_mail(
            subject=self.title,
            message=self.message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.recipient_email],
            fail_silently=False
        )
        
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
        return True
    
    def _send_push(self):
        """Send push notification"""
        # TODO: Implement push notification logic
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
        return True
    
    def _send_sms(self):
        """Send SMS notification"""
        # TODO: Implement SMS logic
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
        return True
    
    def can_retry(self):
        """Check if notification can be retried"""
        return self.status == 'failed' and self.retry_count < self.max_retries


class NotificationTemplate(models.Model):
    """
    Notification templates for consistent messaging
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_templates'
    )
    
    # Template Details
    name = models.CharField(max_length=100)
    notification_type = models.CharField(max_length=20, choices=Notification.NOTIFICATION_TYPES)
    channel = models.CharField(max_length=20, choices=Notification.CHANNELS)
    
    # Template Content
    title_template = models.CharField(max_length=200)
    message_template = models.TextField()
    
    # Variables (JSON list of available variables)
    available_variables = models.JSONField(default=list)
    
    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_templates'
        unique_together = ['teacher', 'name']
        indexes = [
            models.Index(fields=['teacher', 'notification_type', 'channel']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.notification_type} - {self.channel})"
    
    def render(self, context):
        """Render template with context variables"""
        title = self.title_template
        message = self.message_template
        
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            title = title.replace(placeholder, str(value))
            message = message.replace(placeholder, str(value))
        
        return title, message


class NotificationLog(models.Model):
    """
    Log of notification actions and events
    """
    ACTION_TYPES = [
        ('created', 'Created'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('retried', 'Retried'),
        ('cancelled', 'Cancelled'),
        ('whatsapp_sent', 'WhatsApp Sent'),
        ('email_sent', 'Email Sent'),
        ('push_sent', 'Push Sent'),
        ('sms_sent', 'SMS Sent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='logs')
    
    # Log Details
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    details = models.TextField(blank=True, null=True)
    payload = models.JSONField(default=dict)  # Store request/response data
    
    # Result
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notification_logs'
        indexes = [
            models.Index(fields=['notification', 'action']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification.title} - {self.action}"


class NotificationBatch(models.Model):
    """
    Batch processing for bulk notifications
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
        related_name='notification_batches'
    )
    
    # Batch Details
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=BATCH_STATUS, default='pending')
    
    # Processing
    total_notifications = models.PositiveIntegerField(default=0)
    sent_notifications = models.PositiveIntegerField(default=0)
    failed_notifications = models.PositiveIntegerField(default=0)
    
    # Timing
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notification_batches'
        indexes = [
            models.Index(fields=['teacher', 'status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.teacher.username} - {self.name}"
    
    def process_batch(self):
        """Process all notifications in batch"""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.save()
        
        notifications = Notification.objects.filter(
            metadata__batch_id=str(self.id),
            status='pending'
        )
        
        for notification in notifications:
            if notification.send():
                self.sent_notifications += 1
            else:
                self.failed_notifications += 1
        
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()