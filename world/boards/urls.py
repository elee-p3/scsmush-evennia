from django.urls import path
from . import views

urlpatterns = [
    # Show all message boards
    path('', views.boards, name='list'),

    # View the board one post at a time. With no post id provided, defaults to a post
    # from the board at our discretion. If post id is provided, shows the detail page
    # focused on the specified post.
    path('<int:board_id>/', views.detail, name='detail'),
    path('<int:board_id>/<int:post_id>', views.detail, name='detail_for_post'),
]
