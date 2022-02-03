from django.conf.urls import url
from world.events import views

urlpatterns = [
    url(
        r"^test/$",
        views.MyFirstViewClass.as_view(),
        name="display_event",
    ),
]