"""
Settings App Tests
"""
from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.hashers import make_password
from accounts.models import User
from settings_app.models import AppSettings
from settings_app.security_log import SecurityLog
import json


class SettingsAPITestCase(APITestCase):
    """Test settings API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            username='test_teacher@example.com',
            email='test_teacher@example.com',
            password='1234'
        )
        self.teacher.user_type = 'teacher'
        self.teacher.save()
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.teacher)
    
    def test_get_settings(self):
        """Test getting teacher settings"""
        response = self.client.get('/api/settings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('center_name', response.data)
        self.assertIn('language', response.data)
        self.assertIn('two_factor_enabled', response.data)
    
    def test_update_settings(self):
        """Test updating settings"""
        settings, _ = AppSettings.objects.get_or_create(teacher=self.teacher)
        
        response = self.client.put(
            f'/api/settings/{settings.id}/',
            {'center_name': 'Updated Center Name'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        settings.refresh_from_db()
        self.assertEqual(settings.center_name, 'Updated Center Name')
    
    def test_change_pin_success(self):
        """Test successful PIN change"""
        response = self.client.post(
            '/api/settings/change_pin/',
            {
                'old_pin': '1234',
                'new_pin': '5678',
                'confirm_pin': '5678'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('PIN changed successfully', response.data['message'])
        
        # Verify security log created
        log = SecurityLog.objects.filter(
            teacher=self.teacher,
            event_type='pin_change'
        ).first()
        self.assertIsNotNone(log)
        self.assertTrue(log.success)
    
    def test_change_pin_wrong_old_pin(self):
        """Test PIN change with wrong old PIN"""
        response = self.client.post(
            '/api/settings/change_pin/',
            {
                'old_pin': '9999',
                'new_pin': '5678',
                'confirm_pin': '5678'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('incorrect', response.data['error'].lower())
        
        # Verify failed attempt logged
        log = SecurityLog.objects.filter(
            teacher=self.teacher,
            event_type='pin_change_failed'
        ).first()
        self.assertIsNotNone(log)
        self.assertFalse(log.success)
    
    def test_change_pin_mismatch_confirmation(self):
        """Test PIN change with mismatched confirmation"""
        response = self.client.post(
            '/api/settings/change_pin/',
            {
                'old_pin': '1234',
                'new_pin': '5678',
                'confirm_pin': '9999'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('do not match', response.data['error'])
    
    def test_change_pin_invalid_format(self):
        """Test PIN change with invalid format"""
        response = self.client.post(
            '/api/settings/change_pin/',
            {
                'old_pin': '1234',
                'new_pin': '12345',  # Too long
                'confirm_pin': '12345'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('4 digits', response.data['error'])
    
    def test_export_data(self):
        """Test data export"""
        response = self.client.get('/api/settings/export_data/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('attachment', response['Content-Disposition'])
        
        # Verify export logged
        log = SecurityLog.objects.filter(
            teacher=self.teacher,
            event_type='data_export'
        ).first()
        self.assertIsNotNone(log)
    
    def test_danger_zone_requires_confirmation(self):
        """Test that danger zone requires exact confirmation text"""
        response = self.client.post(
            '/api/settings/reset_data/',
            {
                'reset_type': 'delete_students',
                'confirmation_text': 'WRONG TEXT'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Confirmation text must be', str(response.data))
    
    def test_danger_zone_with_correct_confirmation(self):
        """Test danger zone with correct confirmation"""
        from students.models import Student
        
        # Create test student
        Student.objects.create(
            teacher=self.teacher,
            name='Test Student',
            phone='+966500000000',
            subscription_type='monthly',
            monthly_price=200
        )
        
        response = self.client.post(
            '/api/settings/reset_data/',
            {
                'reset_type': 'delete_students',
                'confirmation_text': 'DELETE ALL STUDENTS'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items_deleted'], 1)
        self.assertEqual(Student.objects.filter(teacher=self.teacher).count(), 0)


class AppSettingsModelTestCase(TestCase):
    """Test AppSettings model"""
    
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='model_test_teacher@example.com',
            email='model_test_teacher@example.com',
            password='1234'
        )
        self.teacher.user_type = 'teacher'
        self.teacher.save()
    
    def test_settings_creation_with_defaults(self):
        """Test that settings are created with correct defaults"""
        settings = AppSettings.objects.create(teacher=self.teacher)
        
        # Test defaults
        self.assertEqual(settings.language, 'ar')
        self.assertEqual(settings.theme, 'light')
        self.assertEqual(settings.currency, 'SAR')
        self.assertEqual(settings.session_timeout_minutes, 60)
        self.assertTrue(settings.auto_logout_enabled)
        self.assertFalse(settings.two_factor_enabled)
        self.assertEqual(settings.default_session_duration, 60)
    
    def test_settings_one_to_one_relationship(self):
        """Test that each teacher has only one settings instance"""
        settings1 = AppSettings.objects.create(teacher=self.teacher)
        
        # Trying to create another should fail due to OneToOne
        with self.assertRaises(Exception):
            AppSettings.objects.create(teacher=self.teacher)


class SecurityLogTestCase(TestCase):
    """Test SecurityLog model"""
    
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='security_test_teacher@example.com',
            email='security_test_teacher@example.com',
            password='1234'
        )
        self.teacher.user_type = 'teacher'
        self.teacher.save()
    
    def test_security_log_creation(self):
        """Test creating security log entries"""
        log = SecurityLog.objects.create(
            teacher=self.teacher,
            event_type='pin_change',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            details={'old_pin_hash': 'xxx'},
            success=True
        )
        
        self.assertEqual(log.teacher, self.teacher)
        self.assertEqual(log.event_type, 'pin_change')
        self.assertTrue(log.success)
    
    def test_security_log_ordering(self):
        """Test that logs are ordered by created_at descending"""
        log1 = SecurityLog.objects.create(
            teacher=self.teacher,
            event_type='pin_change'
        )
        log2 = SecurityLog.objects.create(
            teacher=self.teacher,
            event_type='data_export'
        )
        
        logs = SecurityLog.objects.all()
        self.assertEqual(logs[0], log2)  # Most recent first
        self.assertEqual(logs[1], log1)
