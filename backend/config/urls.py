from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from attendance.views import (
    AbsensiViewSet,
    CutiViewSet,
    JadwalViewSet,
    LiburanViewSet,
    RekapKehadiranViewSet,
    ShiftViewSet,
)
from core.views import KaryawanViewSet, LokasiViewSet

router = DefaultRouter()
router.register('shifts', ShiftViewSet, basename='shift')
router.register('jadwal', JadwalViewSet, basename='jadwal')
router.register('absensi', AbsensiViewSet, basename='absensi')
router.register('cuti', CutiViewSet, basename='cuti')
router.register('rekap', RekapKehadiranViewSet, basename='rekap')
router.register('karyawan', KaryawanViewSet, basename='karyawan')
router.register('lokasi', LokasiViewSet, basename='lokasi')
router.register('liburan', LiburanViewSet, basename='liburan')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]
