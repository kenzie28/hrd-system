from django.contrib.auth.models import User

DEFAULT_PORTAL_PASSWORD = '123'


def create_portal_login(karyawan, password=DEFAULT_PORTAL_PASSWORD):
    """Create (or reset) the Django User used to log into the employee portal.

    The User's username mirrors the employee's 7-digit karyawan_id. The employee is
    flagged to change the password on first login.
    """
    user, _ = User.objects.get_or_create(username=karyawan.karyawan_id)
    user.set_password(password)
    user.save()
    karyawan.user = user
    karyawan.must_change_password = True
    karyawan.save(update_fields=['user', 'must_change_password'])
    return user
