from django.db import models

class cvImage(models.Model):
    image = models.ImageField(upload_to='images/')
    processed_image = models.ImageField(upload_to='processed/', null=True, blank=True)
    extracted_text = models.TextField(blank=True)
    gpt_response = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']