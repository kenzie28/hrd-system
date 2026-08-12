from django.contrib import admin

from .models import Lokasi


@admin.register(Lokasi)
class LokasiAdmin(admin.ModelAdmin):
    list_display = ['id', 'nama']
