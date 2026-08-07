from evennia.utils import evtable
from math import floor, ceil

from world.combat.aspects import Aspect, LinkedAspect
from world.combat.effects import EFFECTS
from world.combat.combat_functions import interrupt_chance_calc


def generate_header(client_width, header_title):
    left_arts_spacing = floor(client_width / 2.0 - len(header_title) / 2.0) - 1  # -1 for the border
    right_arts_spacing = ceil(client_width / 2.0 - len(header_title) / 2.0) - 1
    header = "|" + "=" * left_arts_spacing + header_title + "=" * right_arts_spacing + "|"
    return header

# creates the approriate evtable object given the contextual bools
def setup_arts_table(client_width, is_sheet=False, is_check=False):
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

def setup_aspects_table(client_width, is_sheet=False):
    if is_sheet:
        table = evtable.EvTable("Name", "Cost",
                                     border_left_char="|", border_right_char="|", border_top_char="",
                                     border_bottom_char="-", width=client_width)
    else:
        table = evtable.EvTable("Name", "Cost",
                                border_left_char="|", border_right_char="|", border_top_char="-",
                                border_bottom_char="-", width=client_width)
    table.reformat_column(1, width=12)
    return table


def get_abbreviations(action):
    effects_list = action.effects.split()
    effects_abbrev = ""
    for effect in effects_list:
        effects_abbrev += EFFECTS[EFFECTS.index(effect)].abbreviation + " "

    return effects_abbrev


# in-place modification of the evtable that populates it with attacks or arts. Note that CmdCheck duplicates this code
# because there wasn't an overdesigned way to have this function take care of that edge case too
def populate_arts_table(table, actions, base_arts, interrupted_action=None, caller=None):
    for action in actions:
        stat_string = action.stat
        if stat_string == "Power":
            stat_string = "PWR"
        else:
            stat_string = "KNW"

        effects_abbrev = get_abbreviations(action)

        ap_string = modify_ap_string(action, base_arts)
        if caller:
            modified_acc = interrupt_chance_calc(caller, interrupted_action, action, for_check_display=True)
            table.add_row(action.name,
                          ap_string,
                          action.dmg,
                          action.acc,
                          stat_string,
                          effects_abbrev,
                          int(modified_acc))
        else:
            table.add_row(action.name,
                          ap_string,
                          action.dmg,
                          action.acc,
                          stat_string,
                          effects_abbrev)
    return table


# in-place modification of the evtable that populates it with aspects
def populate_aspects_table(table: evtable.EvTable, aspects: list[Aspect], equipped_aspects: list[Aspect]=None):
    if equipped_aspects is None:
        equipped_aspects = []

    for aspect in aspects:
        aspect_str = aspect.name
        if aspect.custom_name:
            if aspect.name.lower() == "extra art":
                # if this is the case, assume this is a LinkedArt
                aspect: LinkedAspect
                aspect_str = "{0} ({1}: {2})".format(aspect.custom_name, aspect.name, aspect.linked_art().name)
            else:
                aspect_str = "{0} ({1})".format(aspect.custom_name, aspect.name)
        if aspect in equipped_aspects:
            table.add_row(aspect_str + " |r(e)|n",
                          str(aspect.cost))
        else:
            table.add_row(aspect_str,
                          str(aspect.cost))
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