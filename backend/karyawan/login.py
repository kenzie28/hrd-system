"""Shared portal / admin login credential checks."""

from __future__ import annotations

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.response import Response


def authenticate_karyawan_credentials(karyawan_id: str, password: str):
    """Authenticate an employee login.

    Returns ``(user, None)`` on success, or ``(None, error_response)`` on failure.
    Distinguishes unknown karyawan_id from wrong password (explicit product choice).
    """
    if not User.objects.filter(username=karyawan_id).exists():
        return None, Response(
            {
                'detail': 'ID karyawan tidak ditemukan.',
                'field': 'karyawan_id',
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    user = authenticate(username=karyawan_id, password=password)
    if user is None:
        return None, Response(
            {
                'detail': 'Kata sandi salah.',
                'field': 'password',
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    return user, None
