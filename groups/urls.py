"""
Group URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'groups', views.GroupViewSet, basename='groups')
router.register(r'schedules', views.GroupScheduleViewSet, basename='group-schedules')
router.register(r'materials', views.GroupMaterialViewSet, basename='group-materials')
router.register(r'announcements', views.GroupAnnouncementViewSet, basename='group-announcements')

urlpatterns = [
    path('', include(router.urls)),
]