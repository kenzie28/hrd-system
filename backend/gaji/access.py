"""Module password for Gaji, separate from the admin login.

Any allowlisted admin must still present this password, the same way
State Manager does. The value is shared with the admin frontend gate.
"""
import secrets

from rest_framework.permissions import BasePermission

GAJI_PASSWORD = 'bears'
PASSWORD_HEADER = 'HTTP_X_GAJI_PASSWORD'


def password_matches(provided: str | None) -> bool:
    candidate = (provided or '').encode('utf-8')
    expected = GAJI_PASSWORD.encode('utf-8')
    if len(candidate) != len(expected):
        secrets.compare_digest(expected, expected)
        return False
    return secrets.compare_digest(candidate, expected)


def extract_password(request) -> str:
    header = request.META.get(PASSWORD_HEADER, '') or ''
    if header:
        return str(header)
    if request.method == 'GET':
        return str(request.query_params.get('password') or '')
    data = getattr(request, 'data', None)
    if data is not None:
        return str(data.get('password') or '')
    return ''


class HasGajiPassword(BasePermission):
    """Reject the request unless the caller sent the Gaji module password."""

    message = 'Kata sandi Gaji tidak valid.'

    def has_permission(self, request, view):
        return password_matches(extract_password(request))
