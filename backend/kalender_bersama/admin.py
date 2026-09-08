from django.contrib import admin

from .models import Langganan, NotifikasiDismiss


@admin.register(Langganan)
class LanggananAdmin(admin.ModelAdmin):
    list_display = ['id', 'subscriber', 'target', 'created_at']
    search_fields = [
        'subscriber__nama',
        'subscriber__karyawan_id',
        'target__nama',
        'target__karyawan_id',
    ]


@admin.register(NotifikasiDismiss)
class NotifikasiDismissAdmin(admin.ModelAdmin):
    list_display = ['id', 'subscriber', 'permohonan', 'dismissed_at']
    search_fields = ['subscriber__nama', 'subscriber__karyawan_id']
