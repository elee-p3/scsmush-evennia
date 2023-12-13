r"""
Evennia settings file.

The available options are found in the default settings file found
here:

/root/scsmush_evennia/evennia/evennia/settings_default.py

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "Star Chaser Story MUSH"
GAME_SLOGAN = '"Until the star we follow brings us back to you."'
WEBSERVER_PORTS = [(80, 4005)]

# Make sure to extend the original list of INSTALLED_APPS from the evennia default
# config (i.e., use "+=") or we'll drop all the core evennia and django stuff.
INSTALLED_APPS += [
    "django.contrib.humanize",
    "world.arts",
    "world.boards",
    "world.character",
    "world.minions",
    "world.msgs",
    "world.scenes"
]

# This is an attempt to in-place modify the default evennia TEMPLATE config without copy-pasta
# that can then drift from the expected defaults over time. Will it work? /shrug
TEMPLATES[0]["OPTIONS"]["builtins"] = [ "shared.filters" ]

MULTISESSION_MODE = 1
######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")

DEBUG = True
