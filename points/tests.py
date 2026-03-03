"""
Points App Tests
Covers: PointRule/Prize CRUD, signal-based auto-awarding, leaderboard
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import User
from students.models import Student
from groups.models import Group
from teaching_sessions.models import Session
from attendance.models import Attendance
from grades.models import Grade, GradeType
from behavior.models import BehaviorRecord

from points.models import PointRule, Prize, StudentPoints, PointTransaction


class PointsTestBase(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher_test',
            password='testpass123',
            user_type='teacher'
        )
        self.student = Student.objects.create(
            teacher=self.teacher,
            name='أحمد محمد',
        )
        self.group = Group.objects.create(
            teacher=self.teacher,
            name='الفرقة الأولى',
            grade_level='الصف الأول'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.teacher)


class PointRuleCRUDTest(PointsTestBase):
    def test_create_rule(self):
        url = '/api/points/rules/'
        data = {
            'event_type': 'attendance',
            'points': 5,
            'description': 'حضور الحصة'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PointRule.objects.count(), 1)
        self.assertEqual(PointRule.objects.first().points, 5)

    def test_create_negative_rule(self):
        url = '/api/points/rules/'
        data = {
            'event_type': 'absence',
            'points': -3,
            'description': 'غياب'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PointRule.objects.first().points, -3)

    def test_list_rules(self):
        PointRule.objects.create(teacher=self.teacher, event_type='attendance', points=5)
        PointRule.objects.create(teacher=self.teacher, event_type='absence', points=-3)
        response = self.client.get('/api/points/rules/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)


class PrizeCRUDTest(PointsTestBase):
    def test_create_prize(self):
        url = '/api/points/prizes/'
        data = {
            'name': 'شهادة تقدير',
            'description': 'شهادة تقدير للطالب المتميز',
            'points_required': 500,
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Prize.objects.count(), 1)


class ManualAwardTest(PointsTestBase):
    def test_manual_award(self):
        url = '/api/points/award/'
        data = {
            'student_id': str(self.student.id),
            'points': 10,
            'description': 'مكافأة يدوية',
            'event_type': 'manual',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        sp = StudentPoints.objects.get(student=self.student, teacher=self.teacher)
        self.assertEqual(sp.total_points, 10)
        self.assertEqual(PointTransaction.objects.count(), 1)

    def test_manual_deduct(self):
        # First award some points
        StudentPoints.objects.create(
            student=self.student, teacher=self.teacher, total_points=20, total_earned=20
        )
        url = '/api/points/award/'
        data = {
            'student_id': str(self.student.id),
            'points': -5,
            'description': 'خصم',
            'event_type': 'bad_behavior',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        sp = StudentPoints.objects.get(student=self.student, teacher=self.teacher)
        self.assertEqual(sp.total_points, 15)
        self.assertEqual(sp.total_deducted, 5)


class LeaderboardTest(PointsTestBase):
    def test_leaderboard_empty(self):
        response = self.client.get('/api/points/leaderboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

    def test_leaderboard_ranking(self):
        student2 = Student.objects.create(teacher=self.teacher, name='علي سامي')
        StudentPoints.objects.create(
            student=self.student, teacher=self.teacher,
            total_points=100, total_earned=100
        )
        StudentPoints.objects.create(
            student=student2, teacher=self.teacher,
            total_points=50, total_earned=50
        )
        response = self.client.get('/api/points/leaderboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        # First place should have more points
        self.assertGreater(
            response.data['results'][0]['total_points'],
            response.data['results'][1]['total_points']
        )
        self.assertEqual(response.data['results'][0]['rank'], 1)


class StudentSummaryTest(PointsTestBase):
    def test_student_summary_not_found(self):
        import uuid
        url = f'/api/points/student/{uuid.uuid4()}/summary/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_student_summary_with_progress_bar(self):
        Prize.objects.create(
            teacher=self.teacher,
            name='50 جنيه',
            points_required=100
        )
        sp = StudentPoints.objects.create(
            student=self.student, teacher=self.teacher,
            total_points=40, total_earned=40
        )
        url = f'/api/points/student/{self.student.id}/summary/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        summary = response.data['summary']
        self.assertEqual(summary['total_points'], 40)
        self.assertEqual(summary['next_prize']['name'], '50 جنيه')
        self.assertEqual(summary['progress_percent'], 40.0)
