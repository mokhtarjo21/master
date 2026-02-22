import os
import django
import sys
import json
from django.test.client import Client

# Configure Django settings
sys.path.append('g:\\master app\\master')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_teacher_assistant.settings')
django.setup()

def test_teacher_register():
    c = Client()
    print("Testing /api/auth/teacher-register/ ...")
    
    payload = {
        "username": "ahmed_kamel_v2_new",
        "email": "ahmed.new.test@example.com",
        "pin": "1234",
        "center_name": "Test Center Alpha",
        "first_name": "Ali",
        "last_name": "Ahmad"
    }
    
    response = c.post('/api/auth/teacher-register/', data=json.dumps(payload), content_type='application/json')
    
    if response.status_code == 201:
        print("SUCCESS: Teacher Registered!")
        data = response.json()
        print(json.dumps(data, indent=2))
        return True
    else:
        print(f"FAILED: {response.status_code}")
        print(response.content.decode())
        return False

if __name__ == '__main__':
    test_teacher_register()
