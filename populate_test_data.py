import os
import django
import random
from datetime import date, timedelta, datetime, time
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_teacher_assistant.settings')
django.setup()

from accounts.models import User
from students.models import Student
from groups.models import Group
from teaching_sessions.models import Session
from attendance.models import Attendance
from payments.models import Payment
from grades.models import Grade, GradeType, GradeScale

def populate():
    print("Beginning data population...")

    # 1. Create Teacher
    print("Creating Teacher...")
    teacher_username = "teacher_test"
    teacher_email = "teacher@test.com"
    teacher_pin = "1234"
    
    if User.objects.filter(username=teacher_username).exists():
        teacher = User.objects.get(username=teacher_username)
        print(f"Teacher {teacher_username} already exists.")
    else:
        teacher = User.objects.create_user(
            username=teacher_username,
            email=teacher_email,
            user_type='teacher',
            password='password123'  # Fallback
        )
        teacher.set_teacher_pin(teacher_pin)
        teacher.save()
        print(f"Created Teacher: {teacher_username} (PIN: {teacher_pin})")

    # 2. Create Students
    print("Creating Students...")
    student_data = [
        {"name": "Ahmed Ali", "phone": "+966500000001", "type": "monthly"},
        {"name": "Sara Mohamed", "phone": "+966500000002", "type": "monthly"},
        {"name": "Omar Hassan", "phone": "+966500000003", "type": "per_session"},
        {"name": "Laila Khaled", "phone": "+966500000004", "type": "monthly"},
        {"name": "Youssef Ibrahim", "phone": "+966500000005", "type": "free"},
    ]

    students = []
    for data in student_data:
        student, created = Student.objects.get_or_create(
            name=data["name"],
            teacher=teacher,
            defaults={
                "phone": data["phone"],
                "subscription_type": data["type"],
                "monthly_price": 200.00 if data["type"] == 'monthly' else 0,
                "per_session_price": 50.00 if data["type"] == 'per_session' else 0
            }
        )
        students.append(student)
        if created:
            print(f"Created Student: {student.name} ({student.code})")
        else:
             # Refresh from DB to get code if not created
             print(f"Student {student.name} already exists.")

    # 3. Create Groups
    print("Creating Groups...")
    group_data = [
        {"name": "Math 101", "subject": "Mathematics"},
        {"name": "Physics 101", "subject": "Physics"},
    ]
    
    groups = []
    for data in group_data:
        group, created = Group.objects.get_or_create(
            name=data["name"],
            teacher=teacher,
            defaults={
                "subject": data["subject"],
                "max_students": 20,
                "grade_level": "Grade 10"
            }
        )
        groups.append(group)
        if created:
            print(f"Created Group: {group.name}")
    
    # Enroll students in groups
    from students.models import StudentGroup
    for student in students:
        for group in groups:
            # Randomly enroll (simple logic: enroll everyone in at least one group logic implied by loop but let's just do random)
            # Actually, to make sure we have data, let's enroll everyone in Math 101
            if group.name == "Math 101" or random.choice([True, False]):
                StudentGroup.objects.get_or_create(
                    student=student,
                    group=group,
                    defaults={"is_active": True}
                )
                print(f"Enrolled {student.name} in {group.name}")

    # 4. Create Sessions
    print("Creating Sessions...")
    today = timezone.now().date()
    
    for group in groups:
        # Past sessions (completed)
        for i in range(1, 4):
            date_past = today - timedelta(days=i*7)
            session, created = Session.objects.get_or_create(
                group=group,
                date=date_past,
                defaults={
                    "start_time": time(10, 0, 0),
                    "end_time": time(11, 30, 0),
                    "status": "completed",
                    "title": f"Lesson {i}"
                }
            )
            
            # 5. Create Attendance for past sessions
            if created or session.status == 'completed':
                # Check coverage logic: simplistic
                for student in students:
                    if StudentGroup.objects.filter(student=student, group=group, is_active=True).exists():
                         status_choice = random.choice(['present', 'present', 'present', 'absent', 'late'])
                         Attendance.objects.get_or_create(
                             session=session,
                             student=student,
                             defaults={"status": status_choice}
                         )
        
        # Future sessions (scheduled)
        for i in range(1, 4):
            date_future = today + timedelta(days=i*7)
            Session.objects.get_or_create(
                group=group,
                date=date_future,
                defaults={
                    "start_time": time(10, 0, 0),
                    "end_time": time(11, 30, 0),
                    "status": "scheduled",
                    "title": f"Upcoming Lesson {i}"
                }
            )

    # 6. Create Payments
    print("Creating Payments...")
    for student in students:
        if student.subscription_type == 'monthly':
            Payment.objects.create(
                student=student,
                amount=student.monthly_price,
                payment_type='monthly',
                payment_date=today - timedelta(days=random.randint(1, 30)),
                due_date=today + timedelta(days=5),
                period_start=today.replace(day=1),
                period_end=(today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
                status='paid',
                amount_paid=student.monthly_price
            )
            print(f"Created Payment for {student.name}")

    # 7. Create Grades
    print("Creating Grades...")
    quiz_type, _ = GradeType.objects.get_or_create(name="Quiz", teacher=teacher, defaults={"weight": 10})
    
    for student in students:
        # Create a grade for a past session if possible, or just a general grade
        # Find a completed session
        completed_session = Session.objects.filter(status='completed').first()
        
        Grade.objects.create(
            student=student,
            grade_type=quiz_type,
            title="Quiz 1",
            score=random.randint(5, 10),
            max_score=10,
            grade_date=today - timedelta(days=5),
            session=completed_session
        )
        print(f"Created Grade for {student.name}")

    print("\nData population complete!")
    print("\n=== Credentials ===")
    print(f"Teacher PIN: {teacher_pin}")
    print("Student Codes:")
    for s in students:
        print(f"  - {s.name}: {s.code}")

if __name__ == '__main__':
    populate()
