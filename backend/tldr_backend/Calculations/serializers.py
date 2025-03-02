from rest_framework import serializers
from .models import cvImage

class cvImageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = cvImage
        fields = ('id', 'image', 'processed_image', 'extracted_text', 'uploaded_at')