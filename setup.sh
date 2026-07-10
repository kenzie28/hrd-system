#!/bin/bash
# =============================================================================
# Local / first-run setup: create admin karyawan Kenzie Mihardja (0000003).
# =============================================================================
# Usage: ./setup.sh
#
# Creates:
#   Lokasi  99 — Headquarters
#   Karyawan 0000003 — Kenzie Mihardja, Director, level 8, no default shift
#
# Portal login is created automatically (default password: 123).
# This karyawan_id is on the HR admin allowlist (core.access).
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/backend"

if [ -f .venv/bin/python ]; then
    PYTHON=.venv/bin/python
elif command -v python3 &>/dev/null; then
    PYTHON=python3
else
    echo "Error: python3 not found. Create a venv in backend/ first."
    exit 1
fi

echo "==> Running migrations..."
"${PYTHON}" manage.py migrate --noinput

echo "==> Creating lokasi and karyawan..."
"${PYTHON}" manage.py shell <<'PY'
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
PY

echo ""
echo "Done. HR admin login: karyawan_id 0000003, password 123 (change on first login)."
