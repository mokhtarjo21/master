"""
Receipt URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'receipts', views.ReceiptViewSet, basename='receipts')
router.register(r'templates', views.ReceiptTemplateViewSet, basename='receipt-templates')
router.register(r'batches', views.ReceiptBatchViewSet, basename='receipt-batches')

urlpatterns = [
    path('', include(router.urls)),
]