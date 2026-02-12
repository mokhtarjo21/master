"""
Parent URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'dashboard', views.ParentDashboardViewSet, basename='parent-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]