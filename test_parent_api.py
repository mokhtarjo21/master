import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_teacher_assistant.settings')
django.setup()

from rest_framework.test import APIClient
from accounts.models import User

# Get the teacher user
teacher = User.objects.filter(user_type='teacher').first()
print(f"Teacher: {teacher.username}")

# Create API client and authenticate
client = APIClient()
client.force_authenticate(user=teacher)

# Test parent creation
parent_data = {
    "name": "Test Parent API",
    "phone": "+966500000099",
    "email": "testparent@example.com",
    "relationship": "Father"
}

print(f"\nTesting POST /api/students/parents/")
print(f"Data: {parent_data}")

response = client.post('/api/students/parents/', parent_data, format='json')

print(f"\nStatus Code: {response.status_code}")
print(f"Response: {response.data}")

if response.status_code != 201:
    print("\n❌ Parent creation FAILED")
else:
    print("\n✅ Parent creation SUCCESS")
