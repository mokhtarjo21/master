"""
Behavior Assessment URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.BehaviorCategoryViewSet, basename='behavior-category')
router.register(r'records',    views.BehaviorRecordViewSet,   basename='behavior-record')
router.register(r'summaries',  views.BehaviorSummaryViewSet,  basename='behavior-summary')

urlpatterns = [
    path('', include(router.urls)),
]
