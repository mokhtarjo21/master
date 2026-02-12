"""
Smart Teacher Assistant URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication URLs
    path('api/auth/', include('accounts.urls')),
    
    # Core App URLs
    path('api/teachers/', include('teachers.urls')),
    path('api/students/', include('students.urls')),
    path('api/parents/', include('parents.urls')),
    # path('api/groups/', include('groups.urls')),
    #path('api/sessions/', include('sessions.urls')),
    path('api/attendance/', include('attendance.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/receipts/', include('receipts.urls')),
    path('api/grades/', include('grades.urls')),
   # path('api/reports/', include('reports.urls')),
   # path('api/notifications/', include('notifications.urls')),
   # path('api/insights/', include('smart_insights.urls')),
   #path('api/rules/', include('rules_engine.urls')),
   # path('api/settings/', include('settings_app.urls')),
   # path('api/subscriptions/', include('subscriptions.urls')),
   # path('api/exports/', include('exports.urls')),
   # path('api/sync/', include('sync.urls')),
   # path('api/audit/', include('audit_logs.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)