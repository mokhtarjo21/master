"""
Points URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PointRuleViewSet,
    PrizeViewSet,
    PointTransactionViewSet,
    LeaderboardView,
    StudentSummaryView,
    AwardPointsView,
)

router = DefaultRouter()
router.register(r'rules', PointRuleViewSet, basename='point-rules')
router.register(r'prizes', PrizeViewSet, basename='prizes')
router.register(r'transactions', PointTransactionViewSet, basename='point-transactions')

urlpatterns = [
    path('', include(router.urls)),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    path('award/', AwardPointsView.as_view(), name='award-points'),
    path('student/<uuid:student_id>/summary/', StudentSummaryView.as_view(), name='student-summary'),
]
