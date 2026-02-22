import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_teacher_assistant.settings')
django.setup()

from django.contrib.auth import get_user_model
from students.models import Student
from payments.models import Payment
from django.utils import timezone

User = get_user_model()
teacher = User.objects.filter(user_type='teacher').first()

if not teacher:
    print("No teacher found to run tests.")
    exit(1)

# Create a dummy student
student = Student.objects.create(
    teacher=teacher,
    name="Session Test Student",
    phone="01010101010"
)

print(f"Student created. Sub Type: {student.subscription_type}, Remaining Sessions: {student.remaining_sessions}")

if student.subscription_type != 'per_session':
    print("FAIL: Student did not default to per_session")

# Create a payment for 8 sessions
from decimal import Decimal
payment = Payment.objects.create(
    student=student,
    payment_type='session',
    amount=Decimal('150.00'),
    session_count=8,
    due_date=timezone.now().date(),
    created_by=teacher
)

print("Payment created with status pending.")
print("Before paying -> Student Remaining Sessions:", student.remaining_sessions)

# Mark paid
payment.add_payment(Decimal('150.00'), 'cash')
payment.refresh_from_db()
student.refresh_from_db()

print("Payment Status:", payment.status)
print("After paying -> Student Remaining Sessions:", student.remaining_sessions)

if student.remaining_sessions == 8:
    print("SUCCESS: 8 Sessions were allocated automatically.")
else:
    print("FAIL: Expected 8 sessions, got", student.remaining_sessions)

# Clean up
payment.delete()
student.user.delete()
student.delete()
