from django import template

register = template.Library()

@register.filter
def convert_newlines(input):
    # converts evennia newlines and the automatically generated xhtml line breaks to \n
    output = input.replace("|/", "<br>").replace("<br />", "<br>")
    return output