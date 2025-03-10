from django.shortcuts import render
from awwwwwwwwwwwwwwwwwwwwwwwwwwwww_framework import generics, status
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

from .models import cvImage, TextHistory, Question
from .serializers import cvImageSerializer, TextHistorySerializer, QuestionSerializer

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
            # Log incoming request
            logger.debug(f"Received image upload request: {request.FILES}")
            
            image_file = request.FILES.get('image')
            if not image_file:
                return Response(
                    {'error': 'No image provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate image file
            if not image_file.content_type.startswith('image/'):
                return Response(
                    {'error': 'File must be an image'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create and save the image instance
            image_instance = cvImage(image=image_file)
            image_instance.save()

            # Process the image and extract text
            try:
                detector = DetectText()
                result = detector.process_django_image(image_instance.image)
                
                # Update instance with extracted text
                image_instance.extracted_text = result['extracted_text']
                
                # Save extracted text to history
                text_history = TextHistory.objects.create(
                    text=result['extracted_text'],
                    source_image=image_instance
                )

                # Process text with GPT
                gpt_client = GPTClient()
                gpt_response = gpt_client.get_response(result['extracted_text'])
                
                Question.objects.create(
                    question_text="Initial analysis",
                    answer=gpt_response,
                    related_text=text_history
                )

                image_instance.gpt_response = gpt_response
                image_instance.save()

            except Exception as processing_error:
                logger.error(f"Error processing image: {str(processing_error)}")
                # Delete the image if processing fails
                image_instance.delete()
                raise processing_error

            # Return response with context
            serializer = self.serializer_class(
                image_instance,
                context={'request': request}
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error in image upload: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TextHistoryViewSet(generics.ListAPIView):
    queryset = TextHistory.objects.all()
    serializer_class = TextHistorySerializer

class QuestionViewSet(generics.ListCreateAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    def post(self, request, *args, **kwargs):
        try:
            text_history_id = request.data.get('text_history_id')
            question_text = request.data.get('question')
            
            text_history = TextHistory.objects.get(id=text_history_id)
            
            gpt_client = GPTClient()
            answer = gpt_client.get_response(text_history.text, question=question_text)
            
            question = Question.objects.create(
                question_text=question_text,
                answer=answer,
                related_text=text_history
            )
            
            serializer = self.serializer_class(question)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )






