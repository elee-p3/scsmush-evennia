def sub_old_ansi(self, text):
    """Replacing old ansi with newer evennia markup strings"""
    if not text:
        return ""
    text = text.replace("%r", "|/")
    text = text.replace("%R", "|/")
    text = text.replace("%t", "|-")
    text = text.replace("%T", "|-")
    text = text.replace("%b", "|_")
    text = text.replace("%cr", "|r")
    text = text.replace("%cR", "|[R")
    text = text.replace("%cg", "|g")
    text = text.replace("%cG", "|[G")
    text = text.replace("%cy", "|!Y")
    text = text.replace("%cY", "|[Y")
    text = text.replace("%cb", "|!B")
    text = text.replace("%cB", "|[B")
    text = text.replace("%cm", "|!M")
    text = text.replace("%cM", "|[M")
    text = text.replace("%cc", "|!C")
    text = text.replace("%cC", "|[C")
    text = text.replace("%cw", "|!W")
    text = text.replace("%cW", "|[W")
    text = text.replace("%cx", "|!X")
    text = text.replace("%cX", "|[X")
    text = text.replace("%ch", "|h")
    text = text.replace("%cn", "|n")
    return text