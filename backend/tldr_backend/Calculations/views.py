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
from .gpt_client import GPTClient

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

            # Process the image and extract text
            detector = DetectText()
            result = detector.process_django_image(image_instance.image)
            
            # Update instance with extracted text
            image_instance.extracted_text = result['extracted_text']
            
            # Process text with GPT
            gpt_client = GPTClient()
            gpt_response = gpt_client.get_response(result['extracted_text'])
            image_instance.gpt_response = gpt_response
            
            # Save all updates
            image_instance.save()

            # Return response with context
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






