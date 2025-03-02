from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.base import ContentFile
import base64
import logging

from .models import cvImage
from .serializers import cvImageSerializer

logger = logging.getLogger(__name__)

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
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        try:
            image_file = request.FILES.get('image')
            if not image_file:
                return Response(
                    {'error': 'No image provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Add request to serializer context
            serializer = self.serializer_class(
                data={'image': image_file},
                context={'request': request}  # Add this line
            )
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )






