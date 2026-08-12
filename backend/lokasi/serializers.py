from rest_framework import serializers

from .models import Lokasi


class LokasiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lokasi
        fields = ['id', 'nama']

    def update(self, instance, validated_data):
        validated_data.pop('id', None)
        return super().update(instance, validated_data)
