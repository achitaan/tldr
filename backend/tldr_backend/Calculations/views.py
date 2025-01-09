from django.shortcuts import render
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response # Response object
from rest_framework.reverse import reverse

from .models import cvImage
from .serializers import cvImageSerializer

# Create your views here.
@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'images':reverse('image-list', request=request, format=format)
    })

class cvImageList(generics.ListCreateAPIView):
    # Can list out and create Image data
    queryset = cvImage.objects.all()
    serializer_class = cvImageSerializer

class cvImageDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = cvImage.objects.all()
    serializer_class = cvImageSerializer




