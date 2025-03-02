from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.base import ContentFile
import base64
import logging
import cv2
import numpy as np
from .image_processing import DetectText

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

            # Create and save the image instance
            image_instance = cvImage(image=image_file)
            image_instance.save()

            # Process the image
            detector = DetectText()
            result = detector.process_django_image(image_instance.image)

            # Save the processed image
            processed_image_name = f"processed_{image_file.name}"
            with open(os.path.join(settings.MEDIA_ROOT, result['processed_image_path']), 'rb') as f:
                image_instance.processed_image.save(processed_image_name, ContentFile(f.read()), save=False)

            # Save the extracted text
            image_instance.extracted_text = result['extracted_text']
            image_instance.save()

            # Return the response with context
            serializer = self.serializer_class(
                image_instance,
                context={'request': request}
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )






