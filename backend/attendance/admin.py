from django.contrib import admin

from .models import (
    Absensi,
    Jadwal,
    Liburan,
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


@admin.register(RekapKehadiran)
class RekapKehadiranAdmin(admin.ModelAdmin):
    list_display = ['id', 'jadwal', 'status', 'absensi', 'cuti']
    list_filter = ['status']


@admin.register(Liburan)
class LiburanAdmin(admin.ModelAdmin):
    list_display = ['id', 'nama', 'tanggal']
