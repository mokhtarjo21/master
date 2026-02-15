"""
Rules Engine App Configuration
"""
from django.apps import AppConfig


class RulesEngineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rules_engine'
    verbose_name = 'Rules Engine'
    
    def ready(self):
        """Import signals when app is ready"""
        import rules_engine.signals
