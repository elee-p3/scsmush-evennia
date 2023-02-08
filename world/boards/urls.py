from django.urls import path
from . import views

urlpatterns = [
    # Show all message boards
    path('', views.boards, name='list'),

    # View all the posts for a specific board
    path('<int:post_id>/', views.detail, name='detail'),
]