"""
Authentication URLs
"""
from django.urls import path
from . import views

urlpatterns = [
    # Authentication endpoints
    path('teacher-login/', views.teacher_login, name='teacher-login'),
    path('student-login/', views.student_login, name='student-login'),
    path('logout/', views.teacher_logout, name='logout'),
    
    # Profile management
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update-profile'),
    
    # QR code generation
    path('generate-qr/', views.generate_student_qr, name='generate-qr'),
    
    # Session management
    path('session-status/', views.session_status, name='session-status'),
    path('extend-session/', views.extend_session, name='extend-session'),
]