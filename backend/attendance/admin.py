from django.contrib import admin

from .models import (
    Absensi,
    Cuti,
    Jadwal,
    Liburan,
    PermohonanCuti,
    RekapKehadiran,
    Shift,
)


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['id', 'jam_masuk', 'jam_keluar']


@admin.register(Jadwal)
class JadwalAdmin(admin.ModelAdmin):
    list_display = ['id', 'karyawan', 'shift', 'tanggal']
    list_filter = ['tanggal', 'karyawan']


@admin.register(Absensi)
class AbsensiAdmin(admin.ModelAdmin):
    list_display = ['id', 'karyawan', 'lokasi', 'tanggal', 'jam_masuk', 'durasi', 'jam_keluar']
    list_filter = ['tanggal', 'lokasi']


@admin.register(PermohonanCuti)
class PermohonanCutiAdmin(admin.ModelAdmin):
    list_display = ['id', 'karyawan', 'tipe', 'tanggal_mulai', 'tanggal_selesai', 'status', 'supervisor']
    list_filter = ['tipe', 'status']


@admin.register(Cuti)
class CutiAdmin(admin.ModelAdmin):
    list_display = ['id', 'permohonan', 'tanggal', 'karyawan', 'tipe']
    list_filter = ['tanggal', 'permohonan__tipe']


@admin.register(RekapKehadiran)
class RekapKehadiranAdmin(admin.ModelAdmin):
    list_display = ['id', 'jadwal', 'status', 'absensi', 'cuti']
    list_filter = ['status']


@admin.register(Liburan)
class LiburanAdmin(admin.ModelAdmin):
    list_display = ['id', 'nama', 'tanggal']
