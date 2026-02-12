"""
Payment URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'payments', views.PaymentViewSet, basename='payments')
router.register(r'payment-plans', views.PaymentPlanViewSet, basename='payment-plans')
router.register(r'reminders', views.PaymentReminderViewSet, basename='payment-reminders')
router.register(r'methods', views.PaymentMethodViewSet, basename='payment-methods')
router.register(r'transactions', views.PaymentTransactionViewSet, basename='payment-transactions')

urlpatterns = [
    path('', include(router.urls)),
]