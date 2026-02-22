import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_teacher_assistant.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

# Create admin user
admin_user, created = User.objects.get_or_create(
    username='super_admin',
    defaults={
        'email': 'admin@example.com',
        'is_superuser': True,
        'user_type': 'admin'
    }
)
if created:
    admin_user.set_password('adminpass123')
    admin_user.save()

# Get JWT token
refresh = RefreshToken.for_user(admin_user)
access_token = str(refresh.access_token)

client = Client()
headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}

# Hit admin teachers endpoint
print("Hitting /api/admin/teachers/")
response = client.get('/api/admin/teachers/', **headers)
print("Status Code:", response.status_code)

if response.status_code == 200:
    print("SUCCESS: Endpoint returned 200 OK.")
    data = response.json()
    if data:
        print("First Teacher Data:")
        print(data[0])
else:
    print("FAIL: Expected 200, got", response.status_code)
    try:
        print("Response:", response.json())
    except:
        pass
