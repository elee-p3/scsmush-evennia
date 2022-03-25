from django import template

register = template.Library()

@register.filter
def or_default(input, default_value):
    """Shows the given input or, if input is None, the given default value"""
    return input or default_value

@register.filter
def convert_texttags(input):
    # converts evennia newlines and the automatically generated xhtml line breaks to \n
    output = input.replace("|/", "<br>").replace("<br />", "<br>").replace("|-", "      ")
    return output