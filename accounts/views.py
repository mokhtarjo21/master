"""
Authentication Views
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.conf import settings
import uuid

from .models import User, TeacherSession, StudentAccessLog
from .serializers import (
    TeacherLoginSerializer, StudentLoginSerializer,
    UserSerializer, TeacherProfileSerializer, StudentQRSerializer
)


def get_client_ip(request):
    """Extract client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@api_view(['POST'])
@permission_classes([AllowAny])
def teacher_login(request):
    """Teacher PIN-based authentication"""
    serializer = TeacherLoginSerializer(data=request.data)
    if serializer.is_valid():
        teacher = serializer.validated_data['teacher']
        device_info = serializer.validated_data.get('device_info', {})
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(teacher)
        access_token = str(refresh.access_token)
        
        # Create teacher session
        session = TeacherSession.objects.create(
            teacher=teacher,
            session_token=str(uuid.uuid4()),
            expires_at=timezone.now() + timezone.timedelta(minutes=settings.TEACHER_SESSION_TIMEOUT),
            device_info=device_info
        )
        
        # Update user activity
        teacher.is_active_session = True
        teacher.last_activity = timezone.now()
        teacher.save()
        
        return Response({
            'access': access_token,
            'refresh': str(refresh),
            'user': TeacherProfileSerializer(teacher).data,
            'session_token': session.session_token
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def student_login(request):
    """Student/Parent authentication via code, token, or QR"""
    serializer = StudentLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Determine access method
        access_method = 'code'
        if request.data.get('access_token'):
            access_method = 'token'
        elif request.data.get('qr_token'):
            access_method = 'qr'
        
        # Log access attempt
        StudentAccessLog.objects.create(
            user=user,
            access_method=access_method,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True
        )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        # Update last activity
        user.last_activity = timezone.now()
        user.save()
        from students.models import Student
        student = Student.objects.get(user=user)
        student_id = student.id
        return Response({
            'access': access_token,
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'student_id': student_id
        })
    
    # Log failed attempt
    if 'user' in serializer.validated_data:
        user = serializer.validated_data['user']
        access_method = 'code'
        if request.data.get('access_token'):
            access_method = 'token'
        elif request.data.get('qr_token'):
            access_method = 'qr'
            
        StudentAccessLog.objects.create(
            user=user,
            access_method=access_method,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=False
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def teacher_logout(request):
    """Teacher logout and session cleanup"""
    if request.user.user_type == 'teacher':
        # Invalidate active sessions
        TeacherSession.objects.filter(
            teacher=request.user,
            is_active=True
        ).update(is_active=False)
        
        # Update user status
        request.user.is_active_session = False
        request.user.save()
        
        return Response({'message': 'Successfully logged out'})
    
    return Response({'error': 'Only teachers can use this endpoint'}, 
                   status=status.HTTP_403_FORBIDDEN)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Get current user profile"""
    if request.user.user_type == 'teacher':
        serializer = TeacherProfileSerializer(request.user)
    else:
        serializer = UserSerializer(request.user)
    
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update user profile"""
    if request.user.user_type == 'teacher':
        serializer = TeacherProfileSerializer(request.user, data=request.data, partial=True)
    else:
        serializer = UserSerializer(request.user, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_student_qr(request):
    """Generate QR code for student access"""
    if request.user.user_type != 'teacher':
        return Response({'error': 'Only teachers can generate QR codes'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    serializer = StudentQRSerializer(data=request.data)
    print(request.data)
    if serializer.is_valid():
        from students.models import Student
        student_id = serializer.validated_data['student_id']
        
        try:
            student = Student.objects.get(
                id=student_id, 
                teacher=request.user, 
                is_active=True
            )
            
            # Generate QR token for the student's user
            if student.user:
                student.user.generate_qr_token()
                student.user.save()
                
                return Response({
                    'qr_token': student.user.qr_token,
                    'expires_at': student.user.qr_expires_at,
                    'qr_url': f'/api/auth/student-login/?qr_token={student.user.qr_token}'
                })
            else:
                return Response({'error': 'Student has no user account'}, 
                               status=status.HTTP_400_BAD_REQUEST)
                
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, 
                           status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_status(request):
    """Check current session status"""
    if request.user.user_type == 'teacher':
        active_session = TeacherSession.objects.filter(
            teacher=request.user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()
        
        return Response({
            'is_active': bool(active_session),
            'expires_at': active_session.expires_at if active_session else None
        })
    
    return Response({
        'is_active': True,
        'last_activity': request.user.last_activity
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extend_session(request):
    """Extend teacher session"""
    if request.user.user_type == 'teacher':
        active_sessions = TeacherSession.objects.filter(
            teacher=request.user,
            is_active=True,
            expires_at__gt=timezone.now()
        )
        
        new_expiry = timezone.now() + timezone.timedelta(minutes=settings.TEACHER_SESSION_TIMEOUT)
        active_sessions.update(expires_at=new_expiry)
        
        request.user.last_activity = timezone.now()
        request.user.save()
        
        return Response({'expires_at': new_expiry})
    
    return Response({'error': 'Only teachers can extend sessions'}, 
                   status=status.HTTP_403_FORBIDDEN)