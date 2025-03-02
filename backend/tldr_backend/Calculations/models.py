from django.db import models
from django.utils import timezone

class cvImage(models.Model):
    image = models.ImageField(upload_to='images/')
    processed_image = models.ImageField(upload_to='processed/', null=True, blank=True)
    extracted_text = models.TextField(blank=True)
    gpt_response = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-uploaded_at']

class TextHistory(models.Model):
    text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    source_image = models.ForeignKey(cvImage, on_delete=models.CASCADE, related_name='text_history')

    class Meta:
        ordering = ['-created_at']

class Question(models.Model):
    question_text = models.TextField()
    answer = models.TextField()
    related_text = models.ForeignKey(TextHistory, on_delete=models.CASCADE, related_name='questions')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']