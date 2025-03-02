"""
URL configuration for tldr_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('Calculations.urls')),
    path('api_auth/', include('rest_framework.urls')),  # Fixed the auth URL
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # Added media files handling