"""Legacy entry used by docs; prefer: python manage.py ensure_seed_admin."""

from karyawan.seed import ensure_seed_admin

print(ensure_seed_admin())
