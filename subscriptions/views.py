"""
Subscriptions Views
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta, date

from accounts.permissions import IsTeacher
from .models import SubscriptionPlan, TeacherSubscription
from .serializers import (
    SubscriptionPlanSerializer,
    AdminSubscriptionPlanSerializer,
    TeacherSubscriptionSerializer,
    TeacherSubscriptionAdminSerializer,
)


def _is_admin(user):
    return user.is_superuser or user.is_staff or user.user_type == 'admin'


# ── Teacher-facing views ──────────────────────────────────────────────────────

class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """Teacher: view own subscription"""
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
            return Response({'message': 'No active subscription found'}, status=404)


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Teachers & students: read-only plan listing"""
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]
    queryset = SubscriptionPlan.objects.filter(is_active=True).order_by('price')


# ── Admin-only views ──────────────────────────────────────────────────────────

class AdminSubscriptionPlanViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD for subscription plans.
    Requires admin/superuser/staff account.

    Endpoints:
      GET    /api/admin/plans/              — list all plans
      POST   /api/admin/plans/              — create plan
      GET    /api/admin/plans/{id}/         — get plan detail
      PUT    /api/admin/plans/{id}/         — full update
      PATCH  /api/admin/plans/{id}/         — partial update
      DELETE /api/admin/plans/{id}/         — delete (only if no active subscribers)
      POST   /api/admin/plans/{id}/toggle_active/  — activate / deactivate
    """
    serializer_class = AdminSubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'name_ar', 'description']
    ordering_fields = ['price', 'duration_days', 'created_at']
    ordering = ['price']

    def get_queryset(self):
        return SubscriptionPlan.objects.all()

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not _is_admin(request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Admin access required.')

    def destroy(self, request, *args, **kwargs):
        plan = self.get_object()
        active_subs = plan.subscriptions.filter(status='active').count()
        if active_subs > 0:
            return Response(
                {'error': f'Cannot delete plan with {active_subs} active subscriber(s). Deactivate it instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activate or deactivate a plan"""
        plan = self.get_object()
        plan.is_active = not plan.is_active
        plan.save(update_fields=['is_active'])
        return Response({
            'id': str(plan.id),
            'name': plan.name,
            'is_active': plan.is_active,
            'message': 'Plan activated.' if plan.is_active else 'Plan deactivated.'
        })


class AdminTeacherSubscriptionViewSet(viewsets.ModelViewSet):
    """
    Admin management of teacher subscriptions.

    POST   /api/admin/teacher-subscriptions/              — assign plan to teacher
    GET    /api/admin/teacher-subscriptions/              — list all subscriptions
    GET    /api/admin/teacher-subscriptions/{id}/         — detail
    PUT    /api/admin/teacher-subscriptions/{id}/         — update
    DELETE /api/admin/teacher-subscriptions/{id}/         — cancel
    POST   /api/admin/teacher-subscriptions/{id}/extend/  — extend subscription
    POST   /api/admin/teacher-subscriptions/{id}/revoke/  — revoke subscription
    GET    /api/admin/teacher-subscriptions/expiring_soon/ — subscriptions expiring in 7 days
    """
    serializer_class = TeacherSubscriptionAdminSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['teacher__username', 'teacher__email', 'plan__name']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = TeacherSubscription.objects.select_related('teacher', 'plan')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        plan_filter = self.request.query_params.get('plan')
        if plan_filter:
            qs = qs.filter(plan_id=plan_filter)

        return qs

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not _is_admin(request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Admin access required.')

    def create(self, request, *args, **kwargs):
        """Assign a plan to a teacher (create or replace)"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        teacher = serializer.validated_data['teacher']
        plan    = serializer.validated_data['plan']

        # Calculate end_date from plan duration if not provided
        start_date = serializer.validated_data.get('start_date', date.today())
        end_date   = serializer.validated_data.get('end_date')
        if not end_date and plan.duration_days > 0:
            end_date = start_date + timedelta(days=plan.duration_days)

        # Create or update
        sub, created = TeacherSubscription.objects.update_or_create(
            teacher=teacher,
            defaults={
                'plan':       plan,
                'status':     serializer.validated_data.get('status', 'active'),
                'start_date': start_date,
                'end_date':   end_date,
                'auto_renew': serializer.validated_data.get('auto_renew', True),
            }
        )

        response_serializer = self.get_serializer(sub)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def extend(self, request, pk=None):
        """
        Extend subscription by N days.
        POST body: { "days": 30 }
        """
        sub  = self.get_object()
        days = request.data.get('days')
        if not days or not str(days).isdigit() or int(days) <= 0:
            return Response({'error': 'Provide a positive integer for days.'},
                            status=status.HTTP_400_BAD_REQUEST)
        days = int(days)
        base = sub.end_date if sub.end_date and sub.end_date > date.today() else date.today()
        sub.end_date = base + timedelta(days=days)
        sub.status   = 'active'
        sub.save(update_fields=['end_date', 'status'])
        return Response({
            'message':  f'Subscription extended by {days} days.',
            'new_end_date': sub.end_date.isoformat(),
            'status':   sub.status,
        })

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Immediately cancel / revoke a teacher's subscription"""
        sub = self.get_object()
        sub.status   = 'cancelled'
        sub.end_date = date.today()
        sub.save(update_fields=['status', 'end_date'])
        return Response({'message': 'Subscription revoked.', 'status': sub.status})

    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """List subscriptions expiring within the next 7 days"""
        days = int(request.query_params.get('days', 7))
        cutoff = date.today() + timedelta(days=days)
        qs = self.get_queryset().filter(
            status='active', end_date__lte=cutoff, end_date__gte=date.today()
        ).order_by('end_date')
        return Response(self.get_serializer(qs, many=True).data)
