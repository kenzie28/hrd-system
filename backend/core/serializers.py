from rest_framework import serializers

from .models import Lokasi


class LokasiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lokasi
        fields = ['id', 'nama']
