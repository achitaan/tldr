from django.db import models

class cvImage(models.Model):
    image = models.ImageField(upload_to='images/')
    processed_image = models.ImageField(upload_to='processed/', null=True, blank=True)
    extracted_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    # Add any other fields you need

    def __str__(self):
        return f"{self.name} ({self.time})"