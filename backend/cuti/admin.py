from django.contrib import admin

from .models import Cuti, PermohonanCuti


@admin.register(PermohonanCuti)
class PermohonanCutiAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'karyawan', 'tipe', 'tanggal_mulai', 'tanggal_selesai',
        'status', 'supervisor', 'hrd_approver',
    ]
    list_filter = ['tipe', 'status']
    search_fields = ['karyawan__nama', 'karyawan__karyawan_id']


@admin.register(Cuti)
class CutiAdmin(admin.ModelAdmin):
    list_display = ['id', 'permohonan', 'tanggal', 'karyawan', 'tipe']
    list_filter = ['tanggal', 'permohonan__tipe']
