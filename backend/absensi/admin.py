from django.contrib import admin

from .models import Absensi


@admin.register(Absensi)
class AbsensiAdmin(admin.ModelAdmin):
    list_display = ['id', 'karyawan', 'lokasi', 'tanggal', 'jam_masuk', 'durasi', 'jam_keluar']
    list_filter = ['tanggal', 'lokasi']
