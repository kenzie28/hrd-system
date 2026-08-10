from django.contrib import admin

from .models import Liburan


@admin.register(Liburan)
class LiburanAdmin(admin.ModelAdmin):
    list_display = ['id', 'nama', 'tanggal']
