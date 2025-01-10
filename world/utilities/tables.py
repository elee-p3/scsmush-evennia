from evennia.utils import evtable
from world.combat.effects import EFFECTS
from world.combat.combat_functions import interrupt_chance_calc


# creates the approriate evtable object given the contextual bools
def setup_table(client_width, is_sheet=False, is_check=False):
    if is_sheet:
        table = evtable.EvTable("Name", "AP", "Dmg", "Acc", "Stat", "Effects",
                                     border_left_char="|", border_right_char="|", border_top_char="",
                                     border_bottom_char="-", width=client_width)
    else:
        table = evtable.EvTable("Name", "AP", "Dmg", "Acc", "Stat", "Effects",
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


def get_abbreviations(action):
    effects_list = action.effects.split()
    effects_abbrev = ""
    for effect in effects_list:
        effects_abbrev += EFFECTS[EFFECTS.index(effect)].abbreviation + " "

    return effects_abbrev


# in-place modification of the evtable that populates it with attacks or arts. Note that CmdCheck duplicates this code
# because there wasn't an overdesigned way to have this function take care of that edge case too
def populate_table(table, actions, base_arts, interrupted_action=None, caller=None):
    for action in actions:
        stat_string = action.stat
        if stat_string == "Power":
            stat_string = "PWR"
        else:
            stat_string = "KNW"

        effects_abbrev = get_abbreviations(action)

        ap_string = modify_ap_string(action, base_arts)
        if caller:
            modified_acc = interrupt_chance_calc(caller, interrupted_action, action)
            table.add_row(action.name,
                          ap_string,
                          action.dmg,
                          action.acc,
                          stat_string,
                          effects_abbrev,
                          modified_acc)
        else:
            table.add_row(action.name,
                          ap_string,
                          action.dmg,
                          action.acc,
                          stat_string,
                          effects_abbrev)
    return table


def modify_ap_string(action, base_arts):
    # Modify the appearance of the Art in Sheet, Arts, etc., depending on status effects, etc.
    baseline = next(x for x in base_arts if x.name.lower() == action.name.lower())
    # Use the baseline for comparison to check if, e.g., AP cost has gone up or down.
    # Define default ap_string.
    ap_string = "|g" + str(action.ap) + "|n"
    if action.ap < baseline.ap:
        # If the action is more costly than usual, the value is colored red.
        ap_string = "|r" + str(action.ap) + "|n"
    elif action.ap > baseline.ap:
        # If the action is less costly than usual, the value is colored cyan.
        ap_string = "|c" + str(action.ap) + "|n"
    return ap_string