from django.urls import path
from . import views

urlpatterns = [
    path('', views.scenes, name='list'),
    # ex: /polls/5/
    path('<int:scene_id>/', views.detail, name='detail'),
]