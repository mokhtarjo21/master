"""
Subscriptions Views
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsTeacher
from .models import SubscriptionPlan, TeacherSubscription
from .serializers import SubscriptionPlanSerializer, TeacherSubscriptionSerializer


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """Teacher subscription viewset"""
    serializer_class = TeacherSubscriptionSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return TeacherSubscription.objects.filter(teacher=self.request.user)
    
    def list(self, request):
        """Get current subscription"""
        try:
            subscription = TeacherSubscription.objects.get(teacher=request.user)
            subscription.update_usage()
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        except TeacherSubscription.DoesNotExist:
            return Response({
                'message': 'No active subscription found'
            }, status=404)


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Available subscription plans"""
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]
    queryset = SubscriptionPlan.objects.filter(is_active=True)
