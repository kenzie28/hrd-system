from django.contrib import admin

from .models import TunjanganObat


@admin.register(TunjanganObat)
class TunjanganObatAdmin(admin.ModelAdmin):
    list_display = ['id', 'karyawan', 'nominal', 'bulan']
