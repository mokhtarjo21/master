"""
Points Signals
Auto-award or deduct points based on attendance, grades, and behavior events.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


def _get_or_create_student_points(student, teacher):
    from points.models import StudentPoints
    obj, _ = StudentPoints.objects.get_or_create(
        student=student,
        teacher=teacher,
        defaults={'total_points': 0}
    )
    return obj


def _get_rule(teacher, event_type, group=None):
    """
    Resolve point rule: prefer group-specific, fallback to global (group=None).
    """
    from points.models import PointRule
    qs = PointRule.objects.filter(teacher=teacher, event_type=event_type, is_active=True)
    if group:
        rule = qs.filter(group=group).first()
        if rule:
            return rule
    return qs.filter(group__isnull=True).first()


def _create_transaction(student, teacher, points, event_type, description,
                        session=None, grade=None, behavior_record=None, date=None):
    from points.models import PointTransaction
    from django.utils import timezone
    PointTransaction.objects.create(
        student=student,
        teacher=teacher,
        points=points,
        event_type=event_type,
        description=description,
        session=session,
        grade=grade,
        behavior_record=behavior_record,
        date=date or timezone.now().date(),
    )


# ---------------------------------------------------------------------------
# Attendance signal
# ---------------------------------------------------------------------------
@receiver(post_save, sender='attendance.Attendance')
def on_attendance_saved(sender, instance, created, **kwargs):
    if not created:
        return  # only fire on new records

    student = instance.student
    teacher = student.teacher
    session = instance.session

    # Determine the group from session
    group = getattr(session, 'group', None)

    if instance.status == 'present':
        rule = _get_rule(teacher, 'attendance', group)
        if rule and rule.points != 0:
            sp = _get_or_create_student_points(student, teacher)
            sp.add_points(rule.points)
            _create_transaction(
                student, teacher, rule.points, 'attendance',
                'حضور الحصة', session=session, date=session.date if session else None
            )

    elif instance.status == 'absent':
        rule = _get_rule(teacher, 'absence', group)
        if rule and rule.points != 0:
            sp = _get_or_create_student_points(student, teacher)
            sp.add_points(rule.points)
            _create_transaction(
                student, teacher, rule.points, 'absence',
                'غياب عن الحصة', session=session, date=session.date if session else None
            )

    elif instance.status == 'late':
        # Award attendance points first
        att_rule = _get_rule(teacher, 'attendance', group)
        if att_rule and att_rule.points != 0:
            sp = _get_or_create_student_points(student, teacher)
            sp.add_points(att_rule.points)
            _create_transaction(
                student, teacher, att_rule.points, 'attendance',
                'حضور الحصة (متأخر)', session=session, date=session.date if session else None
            )
        # Then deduct late points
        late_rule = _get_rule(teacher, 'late', group)
        if late_rule and late_rule.points != 0:
            sp = _get_or_create_student_points(student, teacher)
            sp.add_points(late_rule.points)
            _create_transaction(
                student, teacher, late_rule.points, 'late',
                'تأخير عن الحصة', session=session, date=session.date if session else None
            )


# ---------------------------------------------------------------------------
# Grade signal
# ---------------------------------------------------------------------------
@receiver(post_save, sender='grades.Grade')
def on_grade_saved(sender, instance, created, **kwargs):
    if not created:
        return

    student = instance.student
    teacher = student.teacher
    session = instance.session

    # Determine event type from grade type name (if it contains keywords)
    grade_type_name = instance.grade_type.name.lower() if instance.grade_type else ''

    if 'واجب' in grade_type_name or 'homework' in grade_type_name:
        event_type = 'homework'
    elif 'إملاء' in grade_type_name or 'dictation' in grade_type_name or 'املاء' in grade_type_name:
        event_type = 'dictation'
    else:
        event_type = 'grade'

    group = getattr(session, 'group', None) if session else None
    rule = _get_rule(teacher, event_type, group)
    if not rule or rule.points == 0:
        return

    # Scale points by student percentage (e.g. 90% of max points)
    try:
        percentage = float(instance.percentage) / 100.0
    except Exception:
        percentage = 1.0

    awarded = round(rule.points * percentage)
    if awarded == 0:
        return

    sp = _get_or_create_student_points(student, teacher)
    sp.add_points(awarded)
    _create_transaction(
        student, teacher, awarded, event_type,
        f"{instance.title} — {instance.percentage}%",
        session=session, grade=instance,
        date=instance.grade_date
    )


# ---------------------------------------------------------------------------
# Behavior signal
# ---------------------------------------------------------------------------
@receiver(post_save, sender='behavior.BehaviorRecord')
def on_behavior_saved(sender, instance, created, **kwargs):
    if not created:
        return

    student = instance.student
    teacher = student.teacher

    # Only deduct for negative behaviors
    if instance.rating not in ('needs_improvement', 'poor'):
        return

    session = instance.session
    group = getattr(session, 'group', None) if session else None
    rule = _get_rule(teacher, 'bad_behavior', group)

    if not rule or rule.points == 0:
        return

    sp = _get_or_create_student_points(student, teacher)
    sp.add_points(rule.points)
    _create_transaction(
        student, teacher, rule.points, 'bad_behavior',
        f"سلوك سيئ: {instance.get_rating_display()}",
        session=session, behavior_record=instance,
        date=instance.date
    )
