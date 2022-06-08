from django.urls import path
from . import views

urlpatterns = [
    path('', views.characterlist, name='list'),
    # ex: /scenes/5/
    # path('<int:scene_id>/', views.detail, name='detail'),
]