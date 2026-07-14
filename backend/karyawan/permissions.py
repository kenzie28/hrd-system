from rest_framework.permissions import BasePermission

from .access import is_admin_allowed
from .models import Karyawan


class IsAdminAllowed(BasePermission):
    """Allow only authenticated users whose Karyawan is on the admin allowlist."""

    message = 'Akun Anda tidak memiliki akses ke HRD Admin.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return False
        karyawan = Karyawan.objects.filter(user=user).first()
        return karyawan is not None and is_admin_allowed(karyawan.karyawan_id)
