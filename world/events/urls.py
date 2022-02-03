from django.urls import path
from world.events import views

urlpatterns = [
    path(
        '',
        views.MyFirstViewClass.as_view(),
        name='events_root',
    ),
    path('/test',
         views.MyFirstViewClass.as_view(),
         name='secondtest'),
]