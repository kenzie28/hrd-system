"""Idempotent seed data used on first deploy / container start."""

from __future__ import annotations

from django.contrib.auth.models import User

from lokasi.models import Lokasi

from .models import Karyawan
from .services import create_portal_login

SEED_KARYAWAN_ID = '0000003'
SEED_KARYAWAN_NAMA = 'Kenzie Mihardja'
SEED_LOKASI_ID = '99'
SEED_LOKASI_NAMA = 'Headquarters'


def ensure_seed_admin(*, force_password: bool = False) -> str:
    """Ensure HQ lokasi + default admin karyawan and portal login exist.

    Returns a short human-readable status line for logs.

    Portal password defaults to ``123`` when the Django user is first created,
    re-linked, still flagged ``must_change_password``, or when
    ``force_password=True``.
    """
    lokasi, _ = Lokasi.objects.update_or_create(
        id=SEED_LOKASI_ID,
        defaults={'nama': SEED_LOKASI_NAMA},
    )

    karyawan, created = Karyawan.objects.update_or_create(
        karyawan_id=SEED_KARYAWAN_ID,
        defaults={
            'nama': SEED_KARYAWAN_NAMA,
            'lokasi_kerja': lokasi,
            'jabatan': 'Director',
            'wilayah': '',
            'level': 8,
        },
    )

    portal_user = User.objects.filter(username=SEED_KARYAWAN_ID).first()
    login_action = 'unchanged'
    # Re-apply default password while first-login change is still required. Recovers
    # linked users with unknown/wrong passwords without overwriting after real change.
    if force_password:
        create_portal_login(karyawan)
        login_action = 'forced password-reset (default 123)'
    elif portal_user is None:
        create_portal_login(karyawan)
        login_action = 'created'
    elif karyawan.user_id is None or karyawan.user_id != portal_user.pk:
        create_portal_login(karyawan)
        login_action = 're-linked'
    elif karyawan.must_change_password:
        create_portal_login(karyawan)
        login_action = 'password-reset (default 123)'

    action = 'Created' if created else 'Updated'
    return (
        f'{action} karyawan {karyawan.karyawan_id} — {karyawan.nama} '
        f'({karyawan.jabatan}, level {karyawan.level}, '
        f'lokasi {lokasi.id} {lokasi.nama}; portal login {login_action})'
    )
