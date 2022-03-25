from django import template

register = template.Library()

@register.filter
def convert_texttags(input):
    # converts evennia newlines and the automatically generated xhtml line breaks to \n
    output = input.replace("|/", "<br>").replace("<br />", "<br>").replace("|-", "      ")
    return output
