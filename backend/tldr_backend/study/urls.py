from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views
router=DefaultRouter()
for name,view in [('courses',views.CourseViewSet),('sources',views.SourceViewSet),('pages',views.PageViewSet),('regions',views.RegionViewSet),('conversations',views.ConversationViewSet),('lessons',views.LessonViewSet),('jobs',views.JobViewSet),('study-items',views.StudyItemViewSet)]:
    router.register(name,view,basename=name)
urlpatterns=[path('status/',views.status),path('status/resume/',views.resume),path('data/',views.delete_data),path('',include(router.urls))]
