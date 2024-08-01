from django import template
from django.urls import reverse

register = template.Library()

@register.inclusion_tag("boards/board_summary.html")
def render_board_summary(board):
    return { "board": board }

@register.inclusion_tag("boards/post_list.html")
def render_post_list(sorted_posts, focused_post):
    return { "sorted_posts": sorted_posts, "focused_post": focused_post }

@register.inclusion_tag("boards/post_nav.html")
def render_post_nav(post, previous, next):
    return { "post": post, "previous": previous, "next": next}

@register.inclusion_tag("boards/post_detail.html")
def render_post_detail(post, body_paragraphs):
    return { "post": post, "body_paragraphs": body_paragraphs }

@register.simple_tag
def get_board_detail_url(board, post=None):
    if post == None:
      return reverse('boards:detail', kwargs={'board_id': board.id})
    
    return reverse('boards:detail_for_post',
                   kwargs={'board_id': board.id, 'post_id': post.id})

@register.simple_tag
def get_focused_style(post_to_style, focused_post):
    return "focused" if post_to_style.id == focused_post.id else ""
