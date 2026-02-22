from django.urls import path, include
from rest_framework.routers import DefaultRouter
from teachers.admin_views import AdminTeacherViewSet

router = DefaultRouter()
router.register(r'teachers', AdminTeacherViewSet, basename='admin-teachers')

urlpatterns = [
    path('', include(router.urls)),
]
