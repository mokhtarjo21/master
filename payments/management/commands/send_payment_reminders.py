"""
Management command to send payment reminders
Run daily via cron job or Windows Task Scheduler
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from payments.models import Payment
from notifications.models import Notification


class Command(BaseCommand):
    help = 'Send payment reminders for upcoming and overdue payments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-before',
            type=int,
            default=2,
            help='Days before due date to send reminder (default: 2)'
        )

    def handle(self, *args, **options):
        days_before = options['days_before']
        today = timezone.now().date()
        reminder_date = today + timedelta(days=days_before)
        
        self.stdout.write(self.style.SUCCESS(f'Checking payment reminders for {today}'))
        
        # 1. Upcoming payments (due in X days)
        upcoming_payments = Payment.objects.filter(
            status='pending',
            due_date=reminder_date,
            is_active=True
        ).select_related('student', 'student__teacher')
        
        upcoming_count = 0
        for payment in upcoming_payments:
            student = payment.student
            
            # Check if reminder already sent
            existing_reminder = Notification.objects.filter(
                recipient_id=student.id,
                notification_type='payment_reminder',
                metadata__payment_id=str(payment.id),
                metadata__reminder_type='upcoming'
            ).exists()
            
            if existing_reminder:
                continue
            
            title = f"تذكير: دفعة مستحقة قريباً"
            message = f"عزيزي ولي أمر {student.name}،\n\n"
            message += f"تذكير بأن هناك دفعة مستحقة بعد {days_before} أيام\n"
            message += f"المبلغ: {payment.amount} جنيه\n"
            message += f"تاريخ الاستحقاق: {payment.due_date}\n\n"
            message += "يرجى السداد في الموعد المحدد."
            
            Notification.objects.create(
                teacher=student.teacher,
                recipient_type='student',
                recipient_id=student.id,
                recipient_name=student.name,
                recipient_phone=student.whatsapp_number or student.phone,
                recipient_email=student.email,
                title=title,
                message=message,
                notification_type='payment_reminder',
                channel='whatsapp',
                metadata={
                    'payment_id': str(payment.id),
                    'reminder_type': 'upcoming',
                    'due_date': str(payment.due_date),
                    'amount': str(payment.amount)
                }
            )
            upcoming_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {upcoming_count} upcoming payment reminders')
        )
        
        # 2. Overdue payments
        overdue_payments = Payment.objects.filter(
            status='pending',
            due_date__lt=today,
            is_active=True
        ).select_related('student', 'student__teacher')
        
        overdue_count = 0
        for payment in overdue_payments:
            student = payment.student
            days_overdue = (today - payment.due_date).days
            
            # Only send overdue reminder once per week
            last_reminder = Notification.objects.filter(
                recipient_id=student.id,
                notification_type='payment_reminder',
                metadata__payment_id=str(payment.id),
                metadata__reminder_type='overdue',
                created_at__gte=timezone.now() - timedelta(days=7)
            ).exists()
            
            if last_reminder:
                continue
            
            title = f"⚠️ تنبيه: دفعة متأخرة"
            message = f"عزيزي ولي أمر {student.name}،\n\n"
            message += f"⚠️ هناك دفعة متأخرة منذ {days_overdue} يوم\n"
            message += f"المبلغ: {payment.amount} جنيه\n"
            message += f"تاريخ الاستحقاق: {payment.due_date}\n\n"
            message += "يرجى السداد في أقرب وقت ممكن."
            
            Notification.objects.create(
                teacher=student.teacher,
                recipient_type='student',
                recipient_id=student.id,
                recipient_name=student.name,
                recipient_phone=student.whatsapp_number or student.phone,
                recipient_email=student.email,
                title=title,
                message=message,
                notification_type='payment_reminder',
                channel='whatsapp',
                metadata={
                    'payment_id': str(payment.id),
                    'reminder_type': 'overdue',
                    'due_date': str(payment.due_date),
                    'amount': str(payment.amount),
                    'days_overdue': days_overdue
                }
            )
            overdue_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {overdue_count} overdue payment reminders')
        )
        
        total = upcoming_count + overdue_count
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal reminders sent: {total}')
        )
