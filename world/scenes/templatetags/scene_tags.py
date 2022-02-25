from django import template

register = template.Library()

@register.inclusion_tag("scenes/participants.html")
def show_participants(scene):
    participants = list(scene.participants.all())
    return { "participants": participants }