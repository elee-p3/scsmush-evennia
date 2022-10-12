from evennia import create_help_entry
from evennia.utils import evtable
import csv

# This manually creates the "timeline" help entry by reading the timeline.csv file
# and using evtable to produce an ASCII table readable on the site and in the client.
# NOTE: This produces a bunch of excessive borders and illegible artifacts! Horray!!!!!
# But maybe we can make something of it yet. Step by step.

# First, read the csv file.
with open('world/help/timeline.csv', newline='') as csvfile:
    csvreader = csv.reader(csvfile)
    # The first row will become the headers in the evtable and define the number of columns.
    row1 = next(csvreader)
    timeline_table = evtable.EvTable(row1[0], row1[1], row1[2], row1[3], row1[4], border="cells")
    # Iterate through subsequent rows in the CSV file and add to the evtable
    for row in csvreader:
        timeline_table.add_row(row[0], row[1], row[2], row[3], row[4])

# Create the help entry with the timeline_table as the contents.
entry = create_help_entry("timeline", timeline_table.__str__(), category="theme", locks="view:all()")