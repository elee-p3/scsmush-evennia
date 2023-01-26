from django.urls import path
from . import views

urlpatterns = [

    # Show all message boards
    path('', views.boards, name='list'),
]