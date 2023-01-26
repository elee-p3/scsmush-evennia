from django.shortcuts import render
from world.boards.models import Board

# List page for all boards.
def boards(request):
    all_boards = Board.objects.all()
    context = { "all_boards": all_boards }
    return render(request, "boards/boards.html", context)