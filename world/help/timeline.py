from evennia import create_help_entry
from evennia.utils import evtable
import csv

# This manually creates the "timeline" help entry by reading the timeline.csv file
# and using evtable to produce an ASCII table readable on the site and in the client.

# First, read the csv file.
with open('world/help/timeline.csv', newline='') as csvfile:
    csvreader = csv.reader(csvfile)
    # The first row will become the headers in the evtable and define the number of columns.
    row1 = next(csvreader)
    timeline_table = evtable.EvTable(row1[0], row1[1], row1[2], row1[3], row1[4],
                                 border="cells")
    # Iterate through subsequent rows in the CSV file and add to the evtable
    # Not sure how to skip the first row after using it for the headers above, though.
    for row in csvreader:
        timeline_table.add_row(row)
    # PROBLEM: This doesn't work. It's trying to split a list -- not sure how or why.

# Create the help entry with the timeline_table as the contents.
# I *think* evtable produces a string, in which case, it should theoretically work fine?
entry = create_help_entry("timeline",
                timeline_table,
                category="Theme", locks="view:all()")

# Currently not sure how to *run* create_help_entry, though, and get it to make the help file.
# Can just run it using @py/edit once I get it working!