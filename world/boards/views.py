import re
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseNotFound
from evennia.accounts.models import AccountDB

from world.boards.models import Board, Post

# List page for all boards.
def boards(request):
    all_boards = Board.objects.all()
    context = { "all_boards": all_boards }
    return render(request, "boards/list.html", context)

# Shows a board detail page which doubles as a post detail page. Somewhat like a playlist
# view in a media app, we show one focused post in detail while also showing the list of
# all posts in the board in chronological order.
def detail(request, board_id, post_id=None):
    board = get_object_or_404(Board, pk=board_id)
    sorted_posts = board.posts.order_by('created_at')

    if post_id != None:
        post = get_object_or_404(Post, pk=post_id)

        # Make sure this post actually belongs to the specified board.
        if post.board.id != board.id:
            return HttpResponseNotFound
        
        # Mark the post as viewed by the current user (if there is a current user).
        # This call is idempotent and checks for an existing relationship under the hood,
        # so allowing it to be called again will not create a duplicate relationship.
        if request.user.is_authenticated:
            evennia_account = AccountDB.objects.get(pk=request.user.id)
            post.readers.add(evennia_account)
    else:
        # If no post is explicitly specified, just default to the most recent post.
        post = sorted_posts.last()

    previous, next = _find_prev_and_next(post, sorted_posts)
    
    context = {
        "board": board,
        "post": post,
        "paragraphs": _get_body_paragraphs(post),
        "sorted_posts": sorted_posts,
        "previous": previous,
        "next": next,
        "user": request.user
    }
    return render(request, "boards/detail.html", context)

# Returns a list of strings, each representing a paragraph from the body of the given post.
def _get_body_paragraphs(post):
    return re.split("\s*\n\s*", post.body.strip())

# Retrieves the previous and subsequent posts relative to the given focused_post from the
# list of sorted_posts.
def _find_prev_and_next(focused_post, sorted_posts):
    previous = None
    next = None
    post_found = False
    for post in sorted_posts:
        if post.id == focused_post.id:
            post_found = True
            continue

        if not post_found:
            previous = post
        else:
            next = post
            break

    if not post_found:
        raise ValueError("Invalid arguments: focused_post (id: %s) not found in sorted_posts." % focused_post.id)

    return previous, next
