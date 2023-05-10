from evennia import EvTable


def location_character_search(location):
    location_objects = location.contents
    characters = []
    for obj in location_objects:
        if "Character" in obj.db_typeclass_path:
            characters.append(obj)
    return characters


# creates the approriate evtable object given the contextual bools
def setup_table(client_width, is_sheet=False, is_check=False):
    if is_sheet:
        table = EvTable("Name", "AP", "Dmg", "Acc", "Stat", "Effects",
                                     border_left_char="|", border_right_char="|", border_top_char="",
                                     border_bottom_char="-", width=client_width)
    else:
        table = EvTable("Name", "AP", "Dmg", "Acc", "Stat", "Effects",
                                    border_left_char="|", border_right_char="|", border_top_char="-",
                                    border_bottom_char="-", width=client_width)
    table.reformat_column(1, width=7)
    table.reformat_column(2, width=7)
    table.reformat_column(3, width=7)
    table.reformat_column(4, width=7)

    if is_check:
        table.add_column(header="Int%")
        table.reformat_column(6, width=7)
    return table


# in-place modification of the evtable that populates it with attacks or arts. Note that CmdCheck duplicates this code
# because there wasn't an overdesigned way to have this function take care of that edge case too
def populate_table(table, actions):
    for action in actions:
        stat_string = action.stat
        if stat_string == "Power":
            stat_string = "PWR"
        else:
            stat_string = "KNW"

        table.add_row(action.name,
                      "|g" + str(action.ap) + "|n",
                      action.dmg,
                      action.acc,
                      stat_string,
                      effects_abbreviator(action.effects))
    return table


def effects_abbreviator(effects_string):
    if len(effects_string) <= 2: # i.e. effects is literally "[]"
        return ""
    # example effects_string: "['Bait', 'Weave', 'EX']"
    # generate a list and remove the single quotes
    effects_list = effects_string[1:-1].split(', ')
    # Django TextFields tack on single quotes for each string. Remove them
    effects_list = [effect[1:-1] for effect in effects_list]
    abbreviated_effects = ""
    for effect in effects_list:
        if effect == "Crush":
            abbreviated_effects += "CRU "
        elif effect == "Sweep":
            abbreviated_effects += "SWP "
        elif effect == "Priority":
            abbreviated_effects += "PRI "
        elif effect == "EX":
            abbreviated_effects += "EX "
        elif effect == "Rush":
            abbreviated_effects += "RSH "
        elif effect == "Weave":
            abbreviated_effects += "WV "
        elif effect == "Brace":
            abbreviated_effects += "BRC "
        elif effect == "Bait":
            abbreviated_effects += "BT "

    return abbreviated_effects


def logger(caller, message, level="info"):
    # This is for administrative logging and debugging purposes. Not to be confused with the Scenes system or LogEntry.
    if level == "info":
        caller.msg("|yINFO:|n " + message)
    # We're just putting in this if/else statement provisionally for when we implement more involved debug logging.
    else:
        caller.msg("|cDEBUG:|n " + message)