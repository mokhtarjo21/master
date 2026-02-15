"""
Session URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.SessionViewSet, basename='sessions')
router.register(r'reminders', views.SessionReminderViewSet, basename='session-reminders')
router.register(r'materials', views.SessionMaterialViewSet, basename='session-materials')
router.register(r'notes', views.SessionNoteViewSet, basename='session-notes')

urlpatterns = [
    path('', include(router.urls)),
]