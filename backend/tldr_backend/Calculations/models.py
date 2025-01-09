from django.db import models

# Create your models here.

class cvImage(models.Model):
    name = models.CharField(max_length=100, blank=True, default='')
    image = models.ImageField(upload_to='images/')
    time = models.TimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.time})"