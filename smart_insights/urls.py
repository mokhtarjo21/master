"""
Smart Insights URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'insights', views.InsightViewSet, basename='insights')
router.register(r'alerts', views.AlertViewSet, basename='alerts')
router.register(r'suggestions', views.SuggestionViewSet, basename='suggestions')
router.register(r'analytics', views.AnalyticsViewSet, basename='analytics')
router.register(r'widgets', views.DashboardWidgetViewSet, basename='dashboard-widgets')

urlpatterns = [
    path('', include(router.urls)),
]