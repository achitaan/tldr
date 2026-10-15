from django.urls import include, path
from study.views import serve_media
urlpatterns = [path('api/', include('study.urls')), path('media/<path:path>', serve_media)]
