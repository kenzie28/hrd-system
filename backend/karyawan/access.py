"""Centralized access control config for the HRD admin frontend.

Only employees whose ``karyawan_id`` is listed here may log into the
admin-frontend (HRD) application. Edit this list to grant/revoke access.
"""

ADMIN_LOGIN_ALLOWLIST = [
    '0000003',
    '9610003',
]


def is_admin_allowed(karyawan_id) -> bool:
    return str(karyawan_id) in ADMIN_LOGIN_ALLOWLIST
