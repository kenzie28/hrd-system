from django.contrib import admin

from .models import Absensi, CatatanRekapAbsensi, Kehadiran, RekapAbsensi


@admin.register(Absensi)
class AbsensiAdmin(admin.ModelAdmin):
    list_display = ['id', 'karyawan', 'lokasi', 'tanggal', 'jam_masuk', 'durasi', 'jam_keluar']
    list_filter = ['tanggal', 'lokasi']


class CatatanRekapAbsensiInline(admin.TabularInline):
    model = CatatanRekapAbsensi
    extra = 0
    can_delete = False
    readonly_fields = ['tanggal', 'pesan']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(RekapAbsensi)
class RekapAbsensiAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'month',
        'karyawan',
        'hari_hadir',
        'hari_telat',
        'hari_alpa',
        'hari_keluar_cepat',
        'total_menit_telat',
        'total_menit_lembur',
    ]
    list_filter = ['month']
    inlines = [CatatanRekapAbsensiInline]
    readonly_fields = [
        'month',
        'karyawan',
        'hari_hadir',
        'hari_telat',
        'hari_alpa',
        'hari_keluar_cepat',
        'total_menit_telat',
        'total_menit_lembur',
        'materialized_through',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in ('GET', 'HEAD', 'OPTIONS')

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Kehadiran)
class KehadiranAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'tanggal',
        'karyawan',
        'status',
        'shift',
        'menit_telat',
        'cepat_keluar',
        'lembur',
    ]
    list_filter = ['status', 'tanggal']
    readonly_fields = [
        'karyawan',
        'tanggal',
        'absensi',
        'cuti',
        'permohonan_lembur',
        'shift',
        'menit_telat',
        'cepat_keluar',
        'lembur',
        'status',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in ('GET', 'HEAD', 'OPTIONS')

    def has_delete_permission(self, request, obj=None):
        return False
