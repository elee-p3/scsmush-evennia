from django import template

register = template.Library()

@register.filter
def or_default(input, default_value):
    """Shows the given input or, if input is None, the given default value"""
    return input or default_value

