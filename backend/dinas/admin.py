from django.contrib import admin

from .models import Dinas


@admin.register(Dinas)
class DinasAdmin(admin.ModelAdmin):
    list_display = ['id', 'karyawan', 'tanggal']
    search_fields = ['karyawan__nama', 'karyawan__karyawan_id']
