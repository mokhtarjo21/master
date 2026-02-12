"""
Attendance URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'attendance', views.AttendanceViewSet, basename='attendance')
router.register(r'summaries', views.AttendanceSummaryViewSet, basename='attendance-summaries')
router.register(r'alerts', views.AttendanceAlertViewSet, basename='attendance-alerts')

urlpatterns = [
    path('', include(router.urls)),
    path('qr-scan/<str:qr_token>/', views.qr_scan_attendance, name='qr-scan-attendance'),
]