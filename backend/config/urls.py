from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from absensi.admin_views import AdminAbsensiImportView
from absensi.views import AbsensiViewSet, PortalAbsensiViewSet
from shift.admin_views import AdminShiftImportView
from shift.views import ShiftViewSet
from lokasi.views import LokasiViewSet
from lokasi.admin_views import AdminLokasiImportView, AdminLokasiViewSet
from cuti.admin_views import AdminCutiViewSet
from cuti.views import CutiViewSet, PortalCutiViewSet
from lembur.admin_views import AdminLemburViewSet
from lembur.views import PortalLemburViewSet
from gaji.admin_views import AdminGajiImportView, AdminGajiViewSet
from gaji.views import PortalGajiView
from karyawan.admin_views import (
    AdminKaryawanCreateView,
    AdminKaryawanDetailView,
    AdminKaryawanImportView,
    AdminKaryawanUpdateImportView,
    AdminLoginView,
    AdminMeView,
    AdminResetPasswordView,
)
from karyawan.portal_views import (
    PortalChangePasswordView,
    PortalLoginView,
    PortalMeView,
)
from karyawan.views import KaryawanViewSet
from liburan.admin_views import AdminLiburanImportView, AdminLiburanViewSet
from liburan.views import LiburanViewSet


router = DefaultRouter()
router.register('shifts', ShiftViewSet, basename='shift')
router.register('absensi', AbsensiViewSet, basename='absensi')
router.register('cuti', CutiViewSet, basename='cuti')
router.register('karyawan', KaryawanViewSet, basename='karyawan')
router.register('lokasi', LokasiViewSet, basename='lokasi')
router.register('liburan', LiburanViewSet, basename='liburan')

portal_router = DefaultRouter()
portal_router.register('cuti', PortalCutiViewSet, basename='portal-cuti')
portal_router.register('lembur', PortalLemburViewSet, basename='portal-lembur')
portal_router.register('absensi', PortalAbsensiViewSet, basename='portal-absensi')

admin_router = DefaultRouter()
admin_router.register('cuti', AdminCutiViewSet, basename='admin-cuti')
admin_router.register('lembur', AdminLemburViewSet, basename='admin-lembur')
admin_router.register('gaji', AdminGajiViewSet, basename='admin-gaji')
admin_router.register('liburan', AdminLiburanViewSet, basename='admin-liburan')
admin_router.register('lokasi', AdminLokasiViewSet, basename='admin-lokasi')


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
        'admin/karyawan/import/',
        AdminKaryawanImportView.as_view(),
        name='admin-karyawan-import',
    ),
    path(
        'admin/karyawan/import-update/',
        AdminKaryawanUpdateImportView.as_view(),
        name='admin-karyawan-import-update',
    ),
    path(
        'admin/karyawan/',
        AdminKaryawanCreateView.as_view(),
        name='admin-karyawan-create',
    ),
    path(
        'admin/karyawan/<str:pk>/',
        AdminKaryawanDetailView.as_view(),
        name='admin-karyawan-detail',
    ),
    path(
        'admin/karyawan/<str:pk>/reset-password/',
        AdminResetPasswordView.as_view(),
        name='admin-reset-password',
    ),
    path('admin/gaji/import/', AdminGajiImportView.as_view(), name='admin-gaji-import'),
    path(
        'admin/absensi/import/',
        AdminAbsensiImportView.as_view(),
        name='admin-absensi-import',
    ),
    path(
        'admin/liburan/import/',
        AdminLiburanImportView.as_view(),
        name='admin-liburan-import',
    ),
    path(
        'admin/lokasi/import/',
        AdminLokasiImportView.as_view(),
        name='admin-lokasi-import',
    ),
    path(
        'admin/shift/import/',
        AdminShiftImportView.as_view(),
        name='admin-shift-import',
    ),
    path('admin/', include(admin_router.urls)),
]

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/', include(portal_urlpatterns)),
    path('api/', include(admin_api_urlpatterns)),
    path('api/', include(router.urls)),
]
