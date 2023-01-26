from django.urls import path
from . import views

urlpatterns = [

    # List page for all scenes/logs
    path('', views.scenes, name='list'),

    # View specific scene details
    path('<int:scene_id>/', views.detail, name='detail'),
]