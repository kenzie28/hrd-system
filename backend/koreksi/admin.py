from django.contrib import admin

from .models import Koreksi


@admin.register(Koreksi)
class KoreksiAdmin(admin.ModelAdmin):
    list_display = ['id', 'karyawan', 'tipe', 'nominal', 'bulan']
