from django.urls import path
from . import views

urlpatterns = [
    path('', views.api_root, name='api_root'),
    path('images/', views.cvImageList.as_view(), name='image-list'),
    path('history/', views.TextHistoryViewSet.as_view(), name='text-history'),
    path('questions/', views.QuestionViewSet.as_view(), name='questions'),
]