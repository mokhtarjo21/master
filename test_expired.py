import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_teacher_assistant.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import json

User = get_user_model()
user = User.objects.get(username='ahmed_kamel_v2_new')

# Get JWT token
refresh = RefreshToken.for_user(user)
access_token = str(refresh.access_token)

client = Client()
headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}

# Hit students endpoint
response = client.get('/api/students/', **headers)
print("Status Code:", response.status_code)

if response.status_code == 403:
    print("SUCCESS: Endpoint returned 403 Forbidden for expired trial.")
else:
    print("FAIL: Expected 403, got", response.status_code)
    try:
        print("Response:", response.json())
    except:
        pass
