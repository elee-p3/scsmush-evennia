from evennia import create_help_entry
from csv import reader

# This manually creates the "timeline" help entry by reading the timeline.csv file
# and using evtable to produce an ASCII table readable on the site and in the client.

entry = create_help_entry("timeline",
                "This is a temporary stand-in for the timeline.",
                category="Theme", locks="view:all()")