"""
Grade URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'grade-types', views.GradeTypeViewSet, basename='grade-types')
router.register(r'', views.GradeViewSet, basename='grades')
router.register(r'scales', views.GradeScaleViewSet, basename='grade-scales')
router.register(r'summaries', views.GradeSummaryViewSet, basename='grade-summaries')
router.register(r'alerts', views.GradeAlertViewSet, basename='grade-alerts')

urlpatterns = [
    path('', include(router.urls)),
]