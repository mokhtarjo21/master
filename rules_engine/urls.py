"""
Rules Engine URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'rules', views.RuleViewSet, basename='rules')
router.register(r'executions', views.RuleExecutionViewSet, basename='rule-executions')
router.register(r'templates', views.RuleTemplateViewSet, basename='rule-templates')
router.register(r'rule-sets', views.RuleSetViewSet, basename='rule-sets')

urlpatterns = [
    path('', include(router.urls)),
]