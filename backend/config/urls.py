from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from attendance.views import (
    AbsensiViewSet,
    JadwalViewSet,
    LiburanViewSet,
    RekapKehadiranViewSet,
    ShiftViewSet,
)
from core.admin_views import AdminLoginView, AdminMeView, AdminResetPasswordView
from core.portal_views import (
    PortalChangePasswordView,
    PortalGajiView,
    PortalLoginView,
    PortalMeView,
)
from core.views import KaryawanViewSet, LokasiViewSet
from cuti.admin_views import AdminCutiViewSet
from cuti.views import CutiViewSet, PortalCutiViewSet

router = DefaultRouter()
router.register('shifts', ShiftViewSet, basename='shift')
router.register('jadwal', JadwalViewSet, basename='jadwal')
router.register('absensi', AbsensiViewSet, basename='absensi')
router.register('cuti', CutiViewSet, basename='cuti')
router.register('rekap', RekapKehadiranViewSet, basename='rekap')
router.register('karyawan', KaryawanViewSet, basename='karyawan')
router.register('lokasi', LokasiViewSet, basename='lokasi')
router.register('liburan', LiburanViewSet, basename='liburan')

portal_router = DefaultRouter()
portal_router.register('cuti', PortalCutiViewSet, basename='portal-cuti')

admin_router = DefaultRouter()
admin_router.register('cuti', AdminCutiViewSet, basename='admin-cuti')

portal_urlpatterns = [
    path('portal/login/', PortalLoginView.as_view(), name='portal-login'),
    path('portal/me/', PortalMeView.as_view(), name='portal-me'),
    path(
        'portal/change-password/',
        PortalChangePasswordView.as_view(),
        name='portal-change-password',
    ),
    path('portal/gaji/', PortalGajiView.as_view(), name='portal-gaji'),
    path('portal/', include(portal_router.urls)),
]

admin_api_urlpatterns = [
    path('admin/login/', AdminLoginView.as_view(), name='admin-login'),
    path('admin/me/', AdminMeView.as_view(), name='admin-me'),
    path(
        'admin/karyawan/<int:pk>/reset-password/',
        AdminResetPasswordView.as_view(),
        name='admin-reset-password',
    ),
    path('admin/', include(admin_router.urls)),
]

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/', include(portal_urlpatterns)),
    path('api/', include(admin_api_urlpatterns)),
    path('api/', include(router.urls)),
]
