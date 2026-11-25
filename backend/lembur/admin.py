from django.contrib import admin

from .models import PermohonanLembur


@admin.register(PermohonanLembur)
class PermohonanLemburAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'karyawan', 'tanggal', 'status', 'supervisor', 'hrd_approver',
    ]
    list_filter = ['status']
    search_fields = ['karyawan__nama', 'karyawan__karyawan_id']
