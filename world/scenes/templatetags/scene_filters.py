import re
from django import template
from world.scenes.templatetags.convert_color import short2rgb, ansi2rgb

register = template.Library()

@register.filter
def or_default(input, default_value):
    """Shows the given input or, if input is None, the given default value"""
    return input or default_value

@register.filter
def convert_texttags(input):
    # converts evennia newlines and the automatically generated xhtml line breaks to \n
    output = input.replace("|/", "<br>").replace("<br />", "<br>").replace("|-", "&emsp;")

    # convert xterm colors (and ansi eventually) to rgb and replce the tags with span tags for displaying in html
    # note: possibly consider adding a class tag instead in order to denote a specific function of a color - i.e.
    # instead of just blindly converting a color, define semantically what the point of the color is, and define the
    # actual color in the style sheet
    # the reason that we're not doing this now is because players _might_ include arbitrary colors in their poses as
    # well
    color_tuple_list = re.findall(re.compile("(\|(\d{3}|[A-Za-z])(.*?)\|n)", re.IGNORECASE), output)
    # color_tuple_list = re.findall(re.compile("(\|(\d{3})(.*)\|n)", re.IGNORECASE), output)

    # for each of the names in the list, replace the string with a colored version
    for color_tuple in color_tuple_list:
        # deal with ansi later
        if str(color_tuple[1]).isnumeric():
            rgb = short2rgb(color_tuple[1])
        else:
            rgb = ansi2rgb(color_tuple[1])

        new_color_string = '<span style="color:#{0}">'.format(rgb) + color_tuple[2] + '</span>'
        output = output.replace(color_tuple[0], new_color_string)
    return output
