"""
API Health Check & Verification Script
Run this script to verify that all API endpoints are functioning correctly.
Usage: python api_health_check.py
"""
import os
import django
import sys
import uuid
from datetime import date, timedelta

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_teacher_assistant.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework import status

# Import Models
from students.models import Student
from groups.models import Group
from teaching_sessions.models import Session
from payments.models import Payment  # Note: Check if app is 'payments' or 'payment'
from attendance.models import Attendance

User = get_user_model()

class APIHealthCheck:
    def __init__(self):
        self.client = APIClient()
        self.teacher = None
        self.student = None
        self.token = None
        self.results = {
            'passed': 0,
            'failed': 0,
            'authorization_errors': 0,
            'server_errors': 0
        }
        self.modules = [
            'Auth', 'Teachers', 'Students', 'Parents', 'Groups', 
            'Sessions', 'Attendance', 'Payments', 'Receipts', 
            'Grades', 'Notifications', 'Insights', 'Rules',
            'Reports', 'Settings', 'Subscriptions', 'Exports', 
            'Sync', 'Audit'
        ]

    def print_header(self, title):
        print(f"\n{('=' * 60)}")
        print(f" {title}")
        print(f"{('=' * 60)}")

    def log_result(self, module, endpoint, status_code, expected=200):
        is_success = status_code == expected or (expected == 200 and 200 <= status_code < 300)
        status_icon = "[OK]  " if is_success else "[FAIL]"
        
        print(f"{status_icon} [{module:12}] {endpoint:40} -> {status_code}")
        
        if is_success:
            self.results['passed'] += 1
        else:
            self.results['failed'] += 1
            if status_code == 401:
                self.results['authorization_errors'] += 1
            elif status_code == 403:
                self.results['authorization_errors'] += 1
            elif status_code >= 500:
                self.results['server_errors'] += 1

    def setup_test_data(self):
        self.print_header("SETTING UP TEST DATA")
        
        # Create Teacher
        teacher_email = f"test_teacher_{uuid.uuid4().hex[:6]}@example.com"
        self.teacher, created = User.objects.get_or_create(
            username=teacher_email,
            email=teacher_email,
            defaults={
                'user_type': 'teacher',
                'is_active': True
            }
        )
        if created:
            self.teacher.set_password('testpass123')
            self.teacher.save()
            print(f"Created Test Teacher: {teacher_email}")
        
        # Authenticate
        self.client.force_authenticate(user=self.teacher)
        print("Authenticated as Teacher")
        
        # Create Subscription
        from subscriptions.models import SubscriptionPlan, TeacherSubscription
        plan, _ = SubscriptionPlan.objects.get_or_create(
             name='Free Tier',
             defaults={
                 'price': 0,
                 'max_groups': 2,
                 'description': 'Free Tier Plan'
             }
        )
        TeacherSubscription.objects.get_or_create(
             teacher=self.teacher,
             defaults={
                 'plan': plan,
                 'start_date': date.today(),
                 'end_date': date.today() + timedelta(days=30),
                 'status': 'active'
             }
        )
        print("Created Test Subscription")

    def test_auth_module(self):
        self.print_header("TESTING AUTH MODULE")
        
        # 1. Profile
        response = self.client.get('/api/auth/profile/')
        self.log_result('Auth', 'GET /api/auth/profile/', response.status_code)
        
        # 2. Teacher Login (POST) - unauthenticated
        client = APIClient()
        response = client.post('/api/auth/teacher-login/', {
            'pin': '1234' # Assuming dummy pin
        })
        self.log_result('Auth', 'POST /api/auth/teacher-login/', response.status_code, expected=400) # Expect 400 or 200 depending on valid pin

    def test_students_module(self):
        self.print_header("TESTING STUDENTS MODULE")
        
        # List
        response = self.client.get('/api/students/')
        self.log_result('Students', 'GET /api/students/', response.status_code)
        
        # Create
        data = {
            'name': 'Test Student',
            'phone': '0500000000',
            'grade_level': '10',
            'user': {
                'email': f'student_{uuid.uuid4().hex[:6]}@example.com',
                'password': 'password123'
            }
        }
        # Note: Depending on serializer structure, this might need adjustment
        # response = self.client.post('/api/students/students/', data, format='json')
        # self.log_result('Students', 'POST /api/students/', response.status_code, expected=201)

    def test_groups_module(self):
        self.print_header("TESTING GROUPS MODULE")
        response = self.client.get('/api/groups/')
        self.log_result('Groups', 'GET /api/groups/', response.status_code)

    def test_sessions_module(self):
        self.print_header("TESTING SESSIONS MODULE")
        response = self.client.get('/api/sessions/')
        self.log_result('Sessions', 'GET /api/sessions/', response.status_code)

    def test_attendance_module(self):
        self.print_header("TESTING ATTENDANCE MODULE")
        response = self.client.get('/api/attendance/')
        self.log_result('Attendance', 'GET /api/attendance/', response.status_code)

    def test_payments_module(self):
        self.print_header("TESTING PAYMENTS MODULE")
        response = self.client.get('/api/payments/')
        self.log_result('Payments', 'GET /api/payments/', response.status_code)

    def test_receipts_module(self):
        self.print_header("TESTING RECEIPTS MODULE")
        response = self.client.get('/api/receipts/')
        self.log_result('Receipts', 'GET /api/receipts/', response.status_code)

    def test_grades_module(self):
        self.print_header("TESTING GRADES MODULE")
        response = self.client.get('/api/grades/')
        self.log_result('Grades', 'GET /api/grades/', response.status_code)

    def test_notifications_module(self):
        self.print_header("TESTING NOTIFICATIONS MODULE")
        response = self.client.get('/api/notifications/')
        self.log_result('Notifications', 'GET /api/notifications/', response.status_code)

    def test_insights_module(self):
        self.print_header("TESTING INSIGHTS MODULE")
        response = self.client.get('/api/insights/analytics/dashboard/')
        self.log_result('Insights', 'GET /api/insights/dashboard/', response.status_code)

    def test_rules_module(self):
        self.print_header("TESTING RULES MODULE")
        response = self.client.get('/api/rules/rules/')
        self.log_result('Rules', 'GET /api/rules/', response.status_code)

    def test_new_modules(self):
        self.print_header("TESTING NEW MODULES")
        
        # Reports
        response = self.client.get('/api/reports/reports/')
        self.log_result('Reports', 'GET /api/reports/', response.status_code)
        
        # Settings
        response = self.client.get('/api/settings/settings/')
        # Note: ViewSet might not have list for settings if it's a singleton pattern, but typically ViewSet has list
        self.log_result('Settings', 'GET /api/settings/', response.status_code)
        
        # Subscriptions
        response = self.client.get('/api/subscriptions/')
        self.log_result('Subscriptions', 'GET /api/subscriptions/', response.status_code)
        
        # Exports
        response = self.client.get('/api/exports/exports/')
        self.log_result('Exports', 'GET /api/exports/', response.status_code)
        
        # Sync
        response = self.client.get('/api/sync/status/')
        self.log_result('Sync', 'GET /api/sync/status/', response.status_code)
        
        # Audit
        response = self.client.get('/api/audit/logs/')
        self.log_result('Audit', 'GET /api/audit/logs/', response.status_code)

    def run_all(self):
        try:
            self.setup_test_data()
            self.test_auth_module()
            self.test_students_module()
            self.test_groups_module()
            self.test_sessions_module()
            self.test_attendance_module()
            self.test_payments_module()
            self.test_receipts_module()
            self.test_grades_module()
            self.test_notifications_module()
            self.test_insights_module()
            self.test_rules_module()
            self.test_new_modules()
            
            self.print_header("SUMMARY")
            print(f"Total Tests: {sum(self.results.values())}")
            print(f"Passed:      {self.results['passed']} [OK]")
            print(f"Failed:      {self.results['failed']} [FAIL]")
            print(f"Auth Errors: {self.results['authorization_errors']}")
            print(f"Server errs: {self.results['server_errors']}")
            
        except Exception as e:
            print(f"\nCRITICAL ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    checker = APIHealthCheck()
    checker.run_all()
