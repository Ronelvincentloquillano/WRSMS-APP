from django.apps import AppConfig


class WrsmAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'wrsm_app'

    def ready(self):
        import wrsm_app.signals  # noqa: F401
