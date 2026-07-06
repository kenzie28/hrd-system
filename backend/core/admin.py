from django.contrib import admin

from .models import Karyawan, Lokasi


@admin.register(Lokasi)
class LokasiAdmin(admin.ModelAdmin):
    list_display = ['id', 'nama']


@admin.register(Karyawan)
class KaryawanAdmin(admin.ModelAdmin):
    list_display = ['id', 'nama', 'default_shift']
