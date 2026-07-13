from core.models import Karyawan, Lokasi
from core.services import create_portal_login

lokasi, _ = Lokasi.objects.update_or_create(
    id='99',
    defaults={'nama': 'Headquarters'},
)

karyawan, created = Karyawan.objects.update_or_create(
    karyawan_id='0000003',
    defaults={
        'nama': 'Kenzie Mihardja',
        'lokasi_kerja': lokasi,
        'jabatan': 'Director',
        'wilayah': '',
        'level': 8,
        'default_shift': None,
    },
)

if karyawan.user_id is None:
    create_portal_login(karyawan)

action = 'Created' if created else 'Updated'
print(
    f'{action} karyawan {karyawan.karyawan_id} — {karyawan.nama} '
    f'({karyawan.jabatan}, level {karyawan.level}, lokasi {lokasi.id} {lokasi.nama})'
)
