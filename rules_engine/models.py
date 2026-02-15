"""
Rules Engine Models
Configurable business rules and automation
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class Rule(models.Model):
    """
    Business rules for automation
    """
    RULE_TYPES = [
        ('attendance', 'Attendance Rule'),
        ('payment', 'Payment Rule'),
        ('grade', 'Grade Rule'),
        ('session', 'Session Rule'),
        ('student', 'Student Rule'),
        ('system', 'System Rule'),
    ]
    
    TRIGGER_EVENTS = [
        # Attendance Events
        ('student_absent', 'Student Absent'),
        ('student_late', 'Student Late'),
        
        # Payment Events
        ('payment_created', 'Payment Created'),
        ('payment_overdue', 'Payment Overdue'),
        ('payment_completed', 'Payment Completed'),
        
        # Grade Events
        ('grade_recorded', 'Grade Recorded'),
        ('low_grade', 'Low Grade'),
        ('excellent_grade', 'Excellent Grade'),
        
        # Session Events
        ('session_created', 'Session Created'),
        
        # System Events (future)
        ('daily_check', 'Daily Check'),
        ('weekly_check', 'Weekly Check'),
        ('monthly_check', 'Monthly Check'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rules'
    )
    
    # Rule Details
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    trigger_event = models.CharField(max_length=30, choices=TRIGGER_EVENTS)
    
    # Rule Logic
    conditions = models.JSONField(default=dict)  # Rule conditions
    actions = models.JSONField(default=list)  # Actions to execute
    
    # Configuration
    priority = models.PositiveIntegerField(default=1)  # Execution priority
    is_active = models.BooleanField(default=True)
    
    # Execution Tracking
    last_executed = models.DateTimeField(blank=True, null=True)
    execution_count = models.PositiveIntegerField(default=0)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rules'
        indexes = [
            models.Index(fields=['teacher', 'rule_type', 'is_active']),
            models.Index(fields=['trigger_event', 'is_active']),
            models.Index(fields=['priority']),
        ]
        ordering = ['priority', 'name']
    
    def __str__(self):
        return f"{self.teacher.username} - {self.name}"
    
    def evaluate_conditions(self, context):
        """Evaluate rule conditions against context data"""
        if not self.conditions:
            return True
        
        for condition_key, condition_value in self.conditions.items():
            if not self._evaluate_condition(condition_key, condition_value, context):
                return False
        
        return True
    
    def _evaluate_condition(self, key, condition, context):
        """Evaluate a single condition"""
        if key not in context:
            return False
        
        value = context[key]
        
        if isinstance(condition, dict):
            # Complex condition with operators
            for operator, expected in condition.items():
                if operator == 'eq' and value != expected:
                    return False
                elif operator == 'gt' and value <= expected:
                    return False
                elif operator == 'lt' and value >= expected:
                    return False
                elif operator == 'gte' and value < expected:
                    return False
                elif operator == 'lte' and value > expected:
                    return False
                elif operator == 'in' and value not in expected:
                    return False
                elif operator == 'not_in' and value in expected:
                    return False
        else:
            # Simple equality check
            if value != condition:
                return False
        
        return True
    
    def execute_actions(self, context):
        """Execute rule actions"""
        if not self.actions:
            return []
        
        results = []
        
        for action in self.actions:
            try:
                result = self._execute_action(action, context)
                results.append({
                    'action': action,
                    'status': 'success',
                    'result': result
                })
            except Exception as e:
                results.append({
                    'action': action,
                    'status': 'error',
                    'error': str(e)
                })
        
        # Update execution tracking
        self.last_executed = timezone.now()
        self.execution_count += 1
        self.save(update_fields=['last_executed', 'execution_count'])
        
        return results
    
    def _execute_action(self, action, context):
        """Execute a single action"""
        action_type = action.get('type')
        
        if action_type == 'create_alert':
            return self._create_alert(action, context)
        elif action_type == 'send_notification':
            return self._send_notification(action, context)
        elif action_type == 'update_student':
            return self._update_student(action, context)
        elif action_type == 'create_payment':
            return self._create_payment(action, context)
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    def _create_alert(self, action, context):
        """Create an alert"""
        from smart_insights.models import Alert
        
        alert = Alert.objects.create(
            teacher=self.teacher,
            alert_type=action.get('alert_type', 'system_rule'),
            severity=action.get('severity', 'warning'),
            title=self._render_template(action.get('title', ''), context),
            message=self._render_template(action.get('message', ''), context),
            target_type=context.get('target_type'),
            target_id=context.get('target_id'),
            target_name=context.get('target_name'),
            trigger_data=context
        )
        
        return alert.id
    
    def _send_notification(self, action, context):
        """Send a notification"""
        from notifications.models import Notification
        
        notification = Notification.objects.create(
            teacher=self.teacher,
            recipient_type=action.get('recipient_type', 'student'),
            recipient_id=context.get('student_id') or context.get('parent_id'),
            title=self._render_template(action.get('title', ''), context),
            message=self._render_template(action.get('message', ''), context),
            notification_type=action.get('notification_type', 'alert'),
            channel=action.get('channel', 'whatsapp'),
            metadata={'rule_id': str(self.id), 'context': context}
        )
        
        # Send immediately if requested
        if action.get('send_immediately', False):
            notification.send()
        
        return notification.id
    
    def _update_student(self, action, context):
        """Update student data"""
        from students.models import Student
        
        student_id = context.get('student_id')
        if not student_id:
            raise ValueError("No student_id in context")
        
        student = Student.objects.get(id=student_id, teacher=self.teacher)
        
        updates = action.get('updates', {})
        for field, value in updates.items():
            if hasattr(student, field):
                setattr(student, field, value)
        
        student.save()
        return f"Updated student {student.name}"
    
    def _create_payment(self, action, context):
        """Create a payment"""
        from payments.models import Payment
        from students.models import Student
        
        student_id = context.get('student_id')
        if not student_id:
            raise ValueError("No student_id in context")
        
        student = Student.objects.get(id=student_id, teacher=self.teacher)
        
        payment = Payment.objects.create(
            student=student,
            payment_type=action.get('payment_type', 'monthly'),
            amount=action.get('amount', 0),
            due_date=action.get('due_date', timezone.now().date()),
            notes=self._render_template(action.get('notes', ''), context),
            created_by=self.teacher
        )
        
        return payment.id
    
    def _render_template(self, template, context):
        """Render template with context variables"""
        if not template:
            return ''
        
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            template = template.replace(placeholder, str(value))
        
        return template


class RuleExecution(models.Model):
    """
    Log of rule executions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(Rule, on_delete=models.CASCADE, related_name='executions')
    
    # Execution Details
    trigger_event = models.CharField(max_length=30)
    trigger_data = models.JSONField(default=dict)
    
    # Results
    conditions_met = models.BooleanField()
    actions_executed = models.JSONField(default=list)
    execution_status = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failed', 'Failed'),
    ], default='success')
    
    # Timing
    execution_time = models.DecimalField(max_digits=10, decimal_places=6, default=0)  # Seconds
    
    # System Fields
    executed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rule_executions'
        indexes = [
            models.Index(fields=['rule', 'executed_at']),
            models.Index(fields=['trigger_event', 'executed_at']),
            models.Index(fields=['execution_status']),
        ]
        ordering = ['-executed_at']
    
    def __str__(self):
        return f"{self.rule.name} - {self.executed_at}"


class RuleTemplate(models.Model):
    """
    Pre-defined rule templates
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template Details
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Rule.RULE_TYPES)
    
    # Template Configuration
    template_config = models.JSONField(default=dict)  # Rule template structure
    default_conditions = models.JSONField(default=dict)
    default_actions = models.JSONField(default=list)
    
    # Customization
    customizable_fields = models.JSONField(default=list)  # Fields that can be customized
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rule_templates'
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    def create_rule_for_teacher(self, teacher, customizations=None):
        """Create a rule instance for a teacher"""
        conditions = self.default_conditions.copy()
        actions = self.default_actions.copy()
        
        # Apply customizations
        if customizations:
            for field, value in customizations.items():
                if field in self.customizable_fields:
                    if field.startswith('condition_'):
                        condition_key = field.replace('condition_', '')
                        conditions[condition_key] = value
                    elif field.startswith('action_'):
                        # Update action parameters
                        action_index = int(field.split('_')[1])
                        action_param = '_'.join(field.split('_')[2:])
                        if action_index < len(actions):
                            actions[action_index][action_param] = value
        
        rule = Rule.objects.create(
            teacher=teacher,
            name=self.name,
            description=self.description,
            rule_type=self.category,
            trigger_event=self.template_config.get('trigger_event'),
            conditions=conditions,
            actions=actions
        )
        
        return rule


class RuleSet(models.Model):
    """
    Collection of related rules
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rule_sets'
    )
    
    # Rule Set Details
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    # Configuration
    execution_order = models.CharField(max_length=20, choices=[
        ('priority', 'By Priority'),
        ('sequential', 'Sequential'),
        ('parallel', 'Parallel'),
    ], default='priority')
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rule_sets'
        indexes = [
            models.Index(fields=['teacher', 'is_active']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.teacher.username} - {self.name}"
    
    def get_rules(self):
        """Get rules in this set"""
        return Rule.objects.filter(
            teacher=self.teacher,
            is_active=True
        ).order_by('priority', 'name')
    
    def execute_rules(self, trigger_event, context):
        """Execute all rules in the set for a trigger event"""
        rules = self.get_rules().filter(trigger_event=trigger_event)
        
        results = []
        for rule in rules:
            if rule.evaluate_conditions(context):
                rule_results = rule.execute_actions(context)
                results.extend(rule_results)
        
        return results