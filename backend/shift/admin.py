from django.contrib import admin

from .models import Shift


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['id', 'lokasi_kerja', 'hari', 'jam_masuk', 'jam_keluar']
    list_filter = ['lokasi_kerja', 'hari']
