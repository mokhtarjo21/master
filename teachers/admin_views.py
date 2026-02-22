from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from teachers.models import TeacherProfile
from accounts.serializers import TeacherProfileSerializer


class IsAdminUser(BasePermission):
    """Permission exclusively for the admin account."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'admin'


class AdminTeacherViewSet(viewsets.ModelViewSet):
    """Admin dashboard to manage teachers."""
    permission_classes = [IsAdminUser]
    queryset = TeacherProfile.objects.all()
    serializer_class = TeacherProfileSerializer
    
    def list(self, request, *args, **kwargs):
        """List all teachers with their subscription statuses."""
        profiles = self.get_queryset().select_related('user')
        
        data = []
        for profile in profiles:
            data.append({
                'id': profile.id,
                'user_id': profile.user.id,
                'center_name': profile.center_name,
                'username': profile.user.username,
                'email': profile.user.email,
                'is_active': profile.user.is_active,
                'subscription_plan': profile.subscription_plan,
                'trial_end_date': profile.trial_end_date,
                'subscription_end_date': profile.subscription_end_date,
                'has_active_access': profile.is_active_subscription(),
            })
            
        return Response(data)

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend a teacher's account."""
        profile = self.get_object()
        user = profile.user
        user.is_active = False
        user.save()
        return Response({'message': 'Teacher account suspended.', 'is_active': False})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Re-activate a teacher's account."""
        profile = self.get_object()
        user = profile.user
        user.is_active = True
        user.save()
        return Response({'message': 'Teacher account activated.', 'is_active': True})
        
    @action(detail=True, methods=['post'])
    def update_subscription(self, request, pk=None):
        """Update a teacher's subscription plan and validity."""
        profile = self.get_object()
        
        plan = request.data.get('plan')
        days = request.data.get('days')
        
        if not plan or not days:
            return Response({'error': 'Please provide plan and days.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            days = int(days)
        except ValueError:
            return Response({'error': 'Days must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
            
        profile.subscription_plan = plan
        new_end_date = timezone.now() + timedelta(days=days)
        
        if plan == 'trial':
            profile.trial_end_date = new_end_date
        else:
            profile.subscription_end_date = new_end_date
            
        profile.save()
        
        return Response({
            'message': f'Subscription updated to {plan}',
            'subscription_plan': profile.subscription_plan,
            'trial_end_date': profile.trial_end_date,
            'subscription_end_date': profile.subscription_end_date,
            'has_active_access': profile.is_active_subscription()
        })
