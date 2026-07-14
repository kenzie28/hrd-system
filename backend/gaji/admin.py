from django.contrib import admin

from .models import GajiTemp


@admin.register(GajiTemp)
class GajiTempAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'karyawan',
        'periode',
        'hadir',
        'total_hadir',
        'gaji_pokok',
        'total_gaji',
    ]
    list_filter = ['periode']
    search_fields = ['karyawan__nama', 'karyawan__karyawan_id']
