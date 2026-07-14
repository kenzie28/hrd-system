from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Karyawan
from .services import create_portal_login


@receiver(post_save, sender=Karyawan)
def ensure_portal_login(sender, instance, created, **kwargs):
    if created and instance.karyawan_id and instance.user_id is None:
        create_portal_login(instance)
