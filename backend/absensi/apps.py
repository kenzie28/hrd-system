from django.apps import AppConfig


class AbsensiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'absensi'

    def ready(self):
        from . import signals  # noqa: F401
