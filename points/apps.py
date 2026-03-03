from django.apps import AppConfig


class PointsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'points'
    verbose_name = 'Points & Rewards'

    def ready(self):
        import points.signals  # noqa: F401
