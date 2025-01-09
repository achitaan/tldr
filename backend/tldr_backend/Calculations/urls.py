from django.urls import path
from Calculations import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    path('', views.api_root, name='api_root'),
    path("images/", views.cvImageList.as_view(),name="image-list"),
    path("images/<int:pk>/", views.cvImageList.as_view(),name="cvimage-detail")
]

urlpatterns = format_suffix_patterns(urlpatterns)