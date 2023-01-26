from django.shortcuts import get_object_or_404, render
from world.boards.models import Board

# List page for all boards.
def boards(request):
    all_boards = Board.objects.all()
    context = { "all_boards": all_boards }
    return render(request, "boards/list.html", context)

def detail(request, post_id):
    board = get_object_or_404(Board, pk=post_id)
    sorted_posts = board.posts.order_by('created_at')
    context = {
        "board": board,
        "sorted_posts": sorted_posts,
        "user": request.user
    }
    return render(request, "boards/detail.html", context)
