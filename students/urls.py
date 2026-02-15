"""
Student URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'parents', views.ParentViewSet, basename='parents')
router.register(r'student-parent-links', views.StudentParentLinkViewSet, basename='student-parent-links')
router.register(r'student-groups', views.StudentGroupViewSet, basename='student-groups')
router.register(r'', views.StudentViewSet, basename='students')

urlpatterns = [
    path('', include(router.urls)),
]