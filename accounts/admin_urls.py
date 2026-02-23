from django.urls import path, include
from rest_framework.routers import DefaultRouter
from teachers.admin_views import AdminTeacherViewSet
from accounts.views import admin_login
from subscriptions.views import AdminSubscriptionPlanViewSet, AdminTeacherSubscriptionViewSet

router = DefaultRouter()
router.register(r'teachers',              AdminTeacherViewSet,             basename='admin-teachers')
router.register(r'plans',                 AdminSubscriptionPlanViewSet,    basename='admin-plans')
router.register(r'teacher-subscriptions', AdminTeacherSubscriptionViewSet, basename='admin-teacher-subs')

urlpatterns = [
    path('login/', admin_login, name='admin-login'),
    path('', include(router.urls)),
]
