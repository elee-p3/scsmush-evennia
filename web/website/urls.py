"""
This reroutes from an URL to a python view-function/class.

The main web/urls.py includes these routes for all urls (the root of the url)
so it can reroute to all website pages.

"""

from django.urls import path, include

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns

# add patterns here
urlpatterns = [
    path('boards/', include(("world.boards.urls", "boards"), namespace="boards")),
    path('scenes/', include(("world.scenes.urls", "scenes"), namespace="scenes")),
    path('character/', include(("world.character.urls", "character"), namespace="character"))
]

# read by Django
urlpatterns = urlpatterns + evennia_website_urlpatterns
