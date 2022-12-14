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
        stat_string = action.base_stat
        if stat_string == "Power":
            stat_string = "PWR"
        else:
            stat_string = "KNW"

        table.add_row(action.name,
                      "|g" + str(action.ap_change) + "|n",
                      action.dmg,
                      action.acc,
                      stat_string,
                      effects_abbreviator(action.effects))
    return table

def effects_abbreviator(effects_list):
    effects_string = ""
    for effect in effects_list:
        if effect == "Crush":
            effects_string += "CRU "
        elif effect == "Sweep":
            effects_string += "SWP "
        elif effect == "Priority":
            effects_string += "PRI "
        elif effect == "EX":
            effects_string += "EX "
        elif effect == "Rush":
            effects_string += "RSH "
        elif effect == "Weave":
            effects_string += "WV "
        elif effect == "Brace":
            effects_string += "BRC "
        elif effect == "Bait":
            effects_string += "BT "

    return effects_string