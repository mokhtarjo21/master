"""
Subscriptions App URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.SubscriptionViewSet, basename='subscription')
router.register(r'plans', views.SubscriptionPlanViewSet, basename='plan')

urlpatterns = [
    path('', include(router.urls)),
]
