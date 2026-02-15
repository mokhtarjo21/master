"""
Rules Engine - Signal Integration
Automatically trigger rules based on real events
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
import time

from attendance.models import Attendance
from payments.models import Payment
from grades.models import Grade
from teaching_sessions.models import TeachingSession

from .models import Rule, RuleExecution


def execute_rules_for_event(trigger_event, context, teacher):
    """
    Find and execute all active rules for a trigger event
    """
    # Find matching rules
    rules = Rule.objects.filter(
        teacher=teacher,
        trigger_event=trigger_event,
        is_active=True
    ).order_by('priority')
    
    executed_count = 0
    
    for rule in rules:
        start_time = time.time()
        
        try:
            # Evaluate conditions
            conditions_met = rule.evaluate_conditions(context)
            
            if conditions_met:
                # Execute actions
                actions_executed = rule.execute_actions(context)
                
                # Log successful execution
                execution_time = time.time() - start_time
                RuleExecution.objects.create(
                    rule=rule,
                    trigger_event=trigger_event,
                    trigger_data=context,
                    conditions_met=True,
                    actions_executed=actions_executed,
                    execution_status='success',
                    execution_time=execution_time
                )
                
                executed_count += 1
            else:
                # Log that conditions were not met (optional, for debugging)
                execution_time = time.time() - start_time
                RuleExecution.objects.create(
                    rule=rule,
                    trigger_event=trigger_event,
                    trigger_data=context,
                    conditions_met=False,
                    actions_executed=[],
                    execution_status='skipped',
                    execution_time=execution_time
                )
        
        except Exception as e:
            # Log failed execution
            execution_time = time.time() - start_time
            RuleExecution.objects.create(
                rule=rule,
                trigger_event=trigger_event,
                trigger_data=context,
                conditions_met=False,
                actions_executed=[],
                execution_status='failed',
                execution_time=execution_time
            )
    
    return executed_count


# ============================================================================
# ATTENDANCE SIGNALS
# ============================================================================

@receiver(post_save, sender=Attendance)
def trigger_attendance_rules(sender, instance, created, **kwargs):
    """
    Trigger rules when attendance is recorded
    """
    if not created:
        return
    
    teacher = instance.student.teacher
    
    # Calculate consecutive absences
    consecutive_absences = 0
    if instance.status == 'absent':
        recent_attendance = Attendance.objects.filter(
            student=instance.student,
            date__lt=instance.date
        ).order_by('-date')[:10]
        
        for att in recent_attendance:
            if att.status == 'absent':
                consecutive_absences += 1
            else:
                break
        
        consecutive_absences += 1  # Include current absence
    
    # Build context
    context = {
        'student': instance.student,
        'student_id': str(instance.student.id),
        'student_name': instance.student.name,
        'student_code': instance.student.student_code,
        'status': instance.status,
        'date': str(instance.date),
        'session': instance.session,
        'consecutive_absences': consecutive_absences,
        'notes': instance.notes or '',
    }
    
    # Trigger different events based on status
    if instance.status == 'absent':
        execute_rules_for_event('student_absent', context, teacher)
    elif instance.status == 'late':
        execute_rules_for_event('student_late', context, teacher)


# ============================================================================
# PAYMENT SIGNALS
# ============================================================================

@receiver(post_save, sender=Payment)
def trigger_payment_rules(sender, instance, created, **kwargs):
    """
    Trigger rules when payment is created or updated
    """
    teacher = instance.student.teacher
    
    # Check if payment is overdue
    is_overdue = False
    days_overdue = 0
    
    if instance.due_date and instance.status == 'pending':
        if timezone.now().date() > instance.due_date:
            is_overdue = True
            days_overdue = (timezone.now().date() - instance.due_date).days
    
    # Build context
    context = {
        'student': instance.student,
        'student_id': str(instance.student.id),
        'student_name': instance.student.name,
        'payment_id': str(instance.id),
        'amount': float(instance.amount),
        'amount_paid': float(instance.amount_paid or 0),
        'remaining_amount': float(instance.remaining_amount),
        'status': instance.status,
        'payment_method': instance.payment_method or '',
        'due_date': str(instance.due_date) if instance.due_date else None,
        'is_overdue': is_overdue,
        'days_overdue': days_overdue,
    }
    
    # Trigger appropriate events
    if created:
        execute_rules_for_event('payment_created', context, teacher)
    
    if is_overdue:
        execute_rules_for_event('payment_overdue', context, teacher)
    
    if instance.status == 'paid' and not created:
        execute_rules_for_event('payment_completed', context, teacher)


# ============================================================================
# GRADE SIGNALS
# ============================================================================

@receiver(post_save, sender=Grade)
def trigger_grade_rules(sender, instance, created, **kwargs):
    """
    Trigger rules when grade is recorded
    """
    teacher = instance.student.teacher
    
    # Calculate grade percentage
    grade_percentage = 0
    if instance.max_grade and instance.max_grade > 0:
        grade_percentage = (instance.grade_value / instance.max_grade) * 100
    
    # Determine if grade is low
    is_low_grade = grade_percentage < 50
    is_excellent_grade = grade_percentage >= 90
    
    # Build context
    context = {
        'student': instance.student,
        'student_id': str(instance.student.id),
        'student_name': instance.student.name,
        'grade_id': str(instance.id),
        'subject': instance.subject,
        'grade_value': float(instance.grade_value),
        'max_grade': float(instance.max_grade) if instance.max_grade else 0,
        'grade_percentage': round(grade_percentage, 2),
        'grade_date': str(instance.grade_date),
        'is_low_grade': is_low_grade,
        'is_excellent_grade': is_excellent_grade,
        'notes': instance.notes or '',
    }
    
    # Trigger appropriate events
    if created:
        execute_rules_for_event('grade_recorded', context, teacher)
    
    if is_low_grade:
        execute_rules_for_event('low_grade', context, teacher)
    
    if is_excellent_grade:
        execute_rules_for_event('excellent_grade', context, teacher)


# ============================================================================
# SESSION SIGNALS
# ============================================================================

@receiver(post_save, sender=TeachingSession)
def trigger_session_rules(sender, instance, created, **kwargs):
    """
    Trigger rules when session is created
    """
    if not created:
        return
    
    teacher = instance.group.teacher
    
    # Build context
    context = {
        'session_id': str(instance.id),
        'group': instance.group,
        'group_id': str(instance.group.id),
        'group_name': instance.group.name,
        'session_date': str(instance.session_date),
        'start_time': str(instance.start_time) if instance.start_time else None,
        'end_time': str(instance.end_time) if instance.end_time else None,
        'duration': instance.duration,
        'topic': instance.topic or '',
    }
    
    # Trigger session created event
    execute_rules_for_event('session_created', context, teacher)
