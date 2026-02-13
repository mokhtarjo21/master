"""
Notification URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notifications')
router.register(r'templates', views.NotificationTemplateViewSet, basename='notification-templates')
router.register(r'batches', views.NotificationBatchViewSet, basename='notification-batches')

urlpatterns = [
    path('', include(router.urls)),
]