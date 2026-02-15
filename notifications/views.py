"""
Notification Views
"""
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsTeacher
from .models import Notification, NotificationTemplate, NotificationBatch
from .serializers import (
    NotificationSerializer, NotificationCreateSerializer, BulkNotificationSerializer,
    NotificationTemplateSerializer, NotificationBatchSerializer
)


class NotificationViewSet(viewsets.ModelViewSet):
    """Notification management viewset"""
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'notification_type', 'channel', 'recipient_type']
    search_fields = ['title', 'message', 'recipient_name']
    ordering_fields = ['created_at', 'scheduled_at', 'sent_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Notification.objects.filter(teacher=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return NotificationCreateSerializer
        return NotificationSerializer
    
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Send a specific notification"""
        notification = self.get_object()
        
        if notification.status != 'pending':
            return Response(
                {'error': 'Notification is not in pending status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if notification.send():
            serializer = NotificationSerializer(notification)
            return Response(serializer.data)
        else:
            return Response(
                {'error': f'Failed to send notification: {notification.error_message}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry failed notification"""
        notification = self.get_object()
        
        if not notification.can_retry():
            return Response(
                {'error': 'Notification cannot be retried'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if notification.send():
            serializer = NotificationSerializer(notification)
            return Response(serializer.data)
        else:
            return Response(
                {'error': f'Retry failed: {notification.error_message}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create bulk notifications"""
        serializer = BulkNotificationSerializer(data=request.data)
        if serializer.is_valid():
            recipient_type = serializer.validated_data['recipient_type']
            recipient_ids = serializer.validated_data.get('recipient_ids', [])
            title = serializer.validated_data['title']
            message = serializer.validated_data['message']
            notification_type = serializer.validated_data['notification_type']
            channel = serializer.validated_data['channel']
            scheduled_at = serializer.validated_data.get('scheduled_at', timezone.now())
            
            notifications_created = []
            
            if recipient_type == 'all_students':
                # Send to all active students
                from students.models import Student
                students = Student.objects.filter(
                    teacher=request.user,
                    is_active=True
                )
                
                for student in students:
                    notification = Notification.objects.create(
                        teacher=request.user,
                        recipient_type='student',
                        recipient_id=student.id,
                        recipient_name=student.name,
                        recipient_phone=student.whatsapp_number or student.phone,
                        recipient_email=student.email,
                        title=title,
                        message=message,
                        notification_type=notification_type,
                        channel=channel,
                        scheduled_at=scheduled_at
                    )
                    notifications_created.append(notification)
            
            elif recipient_type in ['student', 'parent']:
                # Send to specific recipients
                if recipient_type == 'student':
                    from students.models import Student
                    recipients = Student.objects.filter(
                        id__in=recipient_ids,
                        teacher=request.user,
                        is_active=True
                    )
                else:  # parent
                    from students.models import Parent
                    recipients = Parent.objects.filter(
                        id__in=recipient_ids,
                        teacher=request.user,
                        is_active=True
                    )
                
                for recipient in recipients:
                    notification = Notification.objects.create(
                        teacher=request.user,
                        recipient_type=recipient_type,
                        recipient_id=recipient.id,
                        recipient_name=recipient.name,
                        recipient_phone=recipient.whatsapp_number or recipient.phone,
                        recipient_email=recipient.email,
                        title=title,
                        message=message,
                        notification_type=notification_type,
                        channel=channel,
                        scheduled_at=scheduled_at
                    )
                    notifications_created.append(notification)
            
            return Response({
                'message': f'Created {len(notifications_created)} notifications',
                'notifications_created': len(notifications_created)
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_send(self, request):
        """Send multiple notifications"""
        notification_ids = request.data.get('notification_ids', [])
        
        if not notification_ids:
            return Response(
                {'error': 'notification_ids is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notifications = self.get_queryset().filter(
            id__in=notification_ids,
            status='pending'
        )
        
        sent_count = 0
        failed_count = 0
        
        for notification in notifications:
            if notification.send():
                sent_count += 1
            else:
                failed_count += 1
        
        return Response({
            'message': f'Processed {len(notifications)} notifications',
            'sent': sent_count,
            'failed': failed_count
        })
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending notifications"""
        queryset = self.get_queryset().filter(status='pending')
        serializer = NotificationSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def failed(self, request):
        """Get failed notifications that can be retried"""
        queryset = self.get_queryset().filter(
            status='failed',
            retry_count__lt=models.F('max_retries')
        )
        serializer = NotificationSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def send_to_student(self, request):
        """Send notification to a single student"""
        from students.models import Student
        
        student_id = request.data.get('student_id')
        title = request.data.get('title')
        message = request.data.get('message')
        notification_type = request.data.get('notification_type', 'announcement')
        channel = request.data.get('channel', 'whatsapp')
        send_immediately = request.data.get('send_immediately', False)
        
        if not all([student_id, title, message]):
            return Response(
                {'error': 'student_id, title, and message are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = Student.objects.get(id=student_id, teacher=request.user, is_active=True)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        
        notification = Notification.objects.create(
            teacher=request.user,
            recipient_type='student',
            recipient_id=student.id,
            recipient_name=student.name,
            recipient_phone=student.whatsapp_number or student.phone,
            recipient_email=student.email,
            title=title,
            message=message,
            notification_type=notification_type,
            channel=channel
        )
        
        if send_immediately:
            notification.send()
        
        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def send_to_group(self, request):
        """Send notification to all students in a group"""
        from groups.models import Group
        
        group_id = request.data.get('group_id')
        title = request.data.get('title')
        message = request.data.get('message')
        notification_type = request.data.get('notification_type', 'announcement')
        channel = request.data.get('channel', 'whatsapp')
        send_immediately = request.data.get('send_immediately', False)
        
        if not all([group_id, title, message]):
            return Response(
                {'error': 'group_id, title, and message are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            group = Group.objects.get(id=group_id, teacher=request.user, is_active=True)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all active students in the group
        student_groups = group.group_students.filter(is_active=True).select_related('student')
        
        notifications_created = []
        for student_group in student_groups:
            student = student_group.student
            notification = Notification.objects.create(
                teacher=request.user,
                recipient_type='student',
                recipient_id=student.id,
                recipient_name=student.name,
                recipient_phone=student.whatsapp_number or student.phone,
                recipient_email=student.email,
                title=title,
                message=message,
                notification_type=notification_type,
                channel=channel,
                metadata={'group_id': str(group.id), 'group_name': group.name}
            )
            
            if send_immediately:
                notification.send()
            
            notifications_created.append(notification)
        
        return Response({
            'message': f'Created {len(notifications_created)} notifications for group {group.name}',
            'notifications_created': len(notifications_created),
            'group_name': group.name
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def send_to_all(self, request):
        """Send notification to all active students"""
        from students.models import Student
        
        title = request.data.get('title')
        message = request.data.get('message')
        notification_type = request.data.get('notification_type', 'announcement')
        channel = request.data.get('channel', 'whatsapp')
        send_immediately = request.data.get('send_immediately', False)
        
        if not all([title, message]):
            return Response(
                {'error': 'title and message are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        students = Student.objects.filter(teacher=request.user, is_active=True)
        
        if not students.exists():
            return Response(
                {'error': 'No active students found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        notifications_created = []
        for student in students:
            notification = Notification.objects.create(
                teacher=request.user,
                recipient_type='student',
                recipient_id=student.id,
                recipient_name=student.name,
                recipient_phone=student.whatsapp_number or student.phone,
                recipient_email=student.email,
                title=title,
                message=message,
                notification_type=notification_type,
                channel=channel
            )
            
            if send_immediately:
                notification.send()
            
            notifications_created.append(notification)
        
        return Response({
            'message': f'Created {len(notifications_created)} notifications for all students',
            'notifications_created': len(notifications_created)
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get notification statistics"""
        queryset = self.get_queryset()
        
        # Apply date filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        stats = queryset.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            sent=Count('id', filter=Q(status='sent')),
            failed=Count('id', filter=Q(status='failed')),
            cancelled=Count('id', filter=Q(status='cancelled'))
        )
        
        # Channel breakdown
        channel_stats = queryset.values('channel').annotate(
            count=Count('id')
        ).order_by('channel')
        
        # Type breakdown
        type_stats = queryset.values('notification_type').annotate(
            count=Count('id')
        ).order_by('notification_type')
        
        stats.update({
            'by_channel': list(channel_stats),
            'by_type': list(type_stats)
        })
        
        return Response(stats)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """Notification template management"""
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['notification_type', 'channel', 'is_active', 'is_default']
    search_fields = ['name', 'title_template', 'message_template']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        return NotificationTemplate.objects.filter(teacher=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set template as default for its type and channel"""
        template = self.get_object()
        
        # Remove default from other templates of same type and channel
        NotificationTemplate.objects.filter(
            teacher=request.user,
            notification_type=template.notification_type,
            channel=template.channel,
            is_default=True
        ).exclude(id=template.id).update(is_default=False)
        
        template.is_default = True
        template.save()
        
        serializer = NotificationTemplateSerializer(template)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """Preview template with sample data"""
        template = self.get_object()
        context = request.data.get('context', {})
        
        try:
            title, message = template.render(context)
            return Response({
                'title': title,
                'message': message,
                'available_variables': template.available_variables
            })
        except Exception as e:
            return Response(
                {'error': f'Template rendering failed: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class NotificationBatchViewSet(viewsets.ModelViewSet):
    """Notification batch management"""
    serializer_class = NotificationBatchSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'started_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return NotificationBatch.objects.filter(teacher=self.request.user)
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process notification batch"""
        batch = self.get_object()
        
        if batch.status != 'pending':
            return Response(
                {'error': 'Batch is not in pending status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process batch in background (in a real app, use Celery)
        batch.process_batch()
        
        serializer = NotificationBatchSerializer(batch)
        return Response(serializer.data)