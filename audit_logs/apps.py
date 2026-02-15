"""
Audit Logs App Configuration
"""
from django.apps import AppConfig


class AuditLogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit_logs'
    
    def ready(self):
        """Import signals when app is ready"""
        import audit_logs.signals
