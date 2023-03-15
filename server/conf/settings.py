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

# Make sure to extend the original list of INSTALLE_APPS from the evennia default
# config (i.e., use "+=") or we'll drop all the core evennia and django stuff.
INSTALLED_APPS += [
    "django.contrib.humanize",
    "web.template_overrides",
    "world.arts",
    "world.character",
    "world.minions",
    "world.msgs",
    "world.scenes"
]

# This is mostly copy-pasta from Evennia default-config to facilitate the addition
# of some global built-ins (which must be specified as TEMPLATES options).
#
# For anything that looks shady/weird, look back at Evennia's settings_default.py for
# comparison / historical context before making changes.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(GAME_DIR, "web", "template_overrides", WEBSITE_TEMPLATE),
            os.path.join(GAME_DIR, "web", "template_overrides", WEBCLIENT_TEMPLATE),
            os.path.join(GAME_DIR, "web", "template_overrides"),
            os.path.join(EVENNIA_DIR, "web", "website", "templates", WEBSITE_TEMPLATE),
            os.path.join(EVENNIA_DIR, "web", "website", "templates"),
            os.path.join(EVENNIA_DIR, "web", "webclient", "templates", WEBCLIENT_TEMPLATE),
            os.path.join(EVENNIA_DIR, "web", "webclient", "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.i18n",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.media",
                "django.template.context_processors.debug",
                "django.contrib.messages.context_processors.messages",
                "sekizai.context_processors.sekizai",
                "evennia.web.utils.general_context.general_context",
            ],
            "debug": DEBUG,
            # THIS is the new part added for SCSMUSH. It adds a set of our own filters
            # and tags (which we created in the new Python package specified below) that
            # can be used throughout the whole project. This is meant for things that are
            # not app-specific and should be easily usable everywhere (e.g., decoding
            # evennia markup).
            # TODO LOOK AT PYTHON2 vs. PYTHON3 dict syntax
            "builtins": [ "shared.filters" ],
        },
    }
]


MULTISESSION_MODE = 1
######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")

DEBUG = True
