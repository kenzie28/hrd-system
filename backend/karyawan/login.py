"""Shared portal / admin login credential checks."""

from __future__ import annotations

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.response import Response


def _auth_error(detail: str, field: str, code: str) -> Response:
    """Return a consistent 401 body the frontends can map to form fields."""
    return Response(
        {
            'detail': detail,
            'field': field,
            'code': code,
        },
        status=status.HTTP_401_UNAUTHORIZED,
    )


def authenticate_karyawan_credentials(karyawan_id: str, password: str):
    """Authenticate an employee login.

    Returns ``(user, None)`` on success, or ``(None, error_response)`` on failure.
    Distinguishes unknown karyawan_id from wrong password (explicit product choice).
    """
    karyawan_id = (karyawan_id or '').strip()

    if not karyawan_id:
        return None, _auth_error(
            'Masukkan ID karyawan.',
            'karyawan_id',
            'missing_username',
        )

    if not User.objects.filter(username=karyawan_id).exists():
        return None, _auth_error(
            'ID karyawan tidak ditemukan.',
            'karyawan_id',
            'invalid_username',
        )

    user = authenticate(username=karyawan_id, password=password)
    if user is None:
        return None, _auth_error(
            'Kata sandi salah.',
            'password',
            'invalid_password',
        )

    return user, None
