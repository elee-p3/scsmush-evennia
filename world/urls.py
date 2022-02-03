from django.conf.urls import url
from . import views

urlpatterns = [
    url(
        "$",
        views.MyFirstViewClass.as_view(),
        name="display_event",
    ),
]