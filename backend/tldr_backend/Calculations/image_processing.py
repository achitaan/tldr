import cv2 as cv
from PIL import Image
from pytesseract import pytesseract
import numpy as np
import tempfile
import os
from django.conf import settings

class DetectText:
    def __init__(self):
        self.imgSize = 2000
        self.binThresh = 180
        self.tesseractPath = r'C:\Users\SSGSS\OneDrive\Programming\Ignition\Tesseract-OCR'  # Update this path

    # ...existing methods...

    def process_django_image(self, image_field):
        """Process an image from Django's ImageField"""
        # Create a temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(image_field.read())
            temp_path = temp_file.name

        try:
            # Process the image
            processed_image = self.process(temp_path)
            
            # Save processed image
            output_path = os.path.join(settings.MEDIA_ROOT, 'processed', 
                                     f'processed_{os.path.basename(image_field.name)}')
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            cv.imwrite(output_path, processed_image)
            
            # Extract text
            text = self.tesseract(temp_path)
            
            return {
                'processed_image_path': os.path.relpath(output_path, settings.MEDIA_ROOT),
                'extracted_text': text
            }
        finally:
            # Clean up temporary file
            os.unlink(temp_path)