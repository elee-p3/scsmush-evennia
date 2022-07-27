"""
Url definition file to redistribute incoming URL requests to django
views. Search the Django documentation for "URL dispatcher" for more
help.

"""
from django.conf.urls import url, include

# Default evennia URLs
from evennia.web.urls import urlpatterns as evennia_urlpatterns
from django.conf.urls import url, include
from world.scenes.urls import urlpatterns as scene_urlpatterns

scsmush_urlpatterns = [
    url('scenes/', include(("world.scenes.urls", "scenes"), namespace="scenes")),
    url('character/', include(("world.character.urls", "character"), namespace="character"))
]

# Set the overall URL patterns for our website to be the union of our own URLs with
# those provided by default in Evennia.
urlpatterns = scsmush_urlpatterns + evennia_urlpatterns