from django import template
from django.urls import reverse

register = template.Library()

@register.inclusion_tag("boards/board_summary.html")
def render_board_summary(board):
    return { "board": board }

@register.inclusion_tag("boards/post_summary.html")
def render_post_summary(post):
    return { "post": post }

@register.simple_tag
def get_board_detail_url(post):
    return reverse('boards:detail', kwargs={'post_id': post.id})

@register.simple_tag
def get_board_detail_url(post):
    return reverse('boards:detail', kwargs={'post_id': post.id})