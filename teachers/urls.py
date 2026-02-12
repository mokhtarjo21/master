"""
Teacher URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'profile', views.TeacherProfileViewSet, basename='teacher-profile')
router.register(r'stats', views.TeacherStatsViewSet, basename='teacher-stats')

urlpatterns = [
    path('', include(router.urls)),
]