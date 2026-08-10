from rest_framework import serializers

from .models import Liburan


class LiburanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Liburan
        fields = ['id', 'nama', 'tanggal']
