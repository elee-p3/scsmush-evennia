from django.urls import path, re_path
from . import views
from evennia.web.website.views.characters import CharacterDetailView

urlpatterns = [
    path('', views.character, name='list'),
    re_path(
        r"^characters/detail/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$",
        CharacterDetailView.as_view(),
        name="character-detail",
    )
]