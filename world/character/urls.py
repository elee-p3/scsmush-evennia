from django.urls import path, re_path
from . import views
from evennia.web.website import views as website_views
from django.conf.urls import url

urlpatterns = [
    path('', views.character, name='list'),
    re_path(
        r"^characters/detail/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$",
        website_views.CharacterDetailView.as_view(),
        name="character-detail",
    )
]