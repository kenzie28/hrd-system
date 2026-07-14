from django.apps import AppConfig


class KaryawanConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'karyawan'
    verbose_name = 'Karyawan'

    def ready(self):
        from . import signals  # noqa: F401
