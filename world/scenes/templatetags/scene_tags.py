from django import template
from django.urls import reverse

register = template.Library()

@register.inclusion_tag("scenes/participants.html")
def show_participants(scene):
    participants = list(scene.participants.all())
    return { "participants": participants }

@register.inclusion_tag("scenes/log_entries.html")
def render_scene_log(scene):
    log_entries = list(scene.logentry_set.all())
    return { "entries" : log_entries }

@register.simple_tag
def get_scene_detail_url(scene):
    return reverse('scenes:detail', kwargs={'scene_id': scene.id})