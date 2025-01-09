from rest_framework import serializers

from .models import cvImage

class cvImageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = cvImage
        fields = ['url', 'id', 'name', 'image', 'time']