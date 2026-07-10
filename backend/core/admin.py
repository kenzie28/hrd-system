from django.contrib import admin

from .models import Karyawan, Lokasi


@admin.register(Lokasi)
class LokasiAdmin(admin.ModelAdmin):
    list_display = ['id', 'nama']


@admin.register(Karyawan)
class KaryawanAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'karyawan_id',
        'nama',
        'lokasi_kerja',
        'jabatan',
        'wilayah',
        'level',
        'default_shift',
        'user',
        'must_change_password',
    ]
    list_filter = ['level', 'lokasi_kerja', 'wilayah']
    search_fields = ['karyawan_id', 'nama']
