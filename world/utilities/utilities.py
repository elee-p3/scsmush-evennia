from evennia.utils import evtable
from world.combat.effects import EFFECTS
from evennia.objects.models import ObjectDB

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
def populate_table(table, actions):
    for action in actions:
        stat_string = action.stat
        if stat_string == "Power":
            stat_string = "PWR"
        else:
            stat_string = "KNW"

        effects_abbrev = get_abbreviations(action)

        table.add_row(action.name,
                      "|g" + str(action.ap) + "|n",
                      action.dmg,
                      action.acc,
                      stat_string,
                      effects_abbrev)
    return table


def logger(caller, message, level="info"):
    # This is for administrative logging and debugging purposes. Not to be confused with the Scenes system or LogEntry.
    if level == "info":
        caller.msg("|yINFO:|n " + message)
    # We're just putting in this if/else statement provisionally for when we implement more involved debug logging.
    else:
        caller.msg("|cDEBUG:|n " + message)


def find_attacker_from_key(attacker_key):
    # This finds the attacker's character object from their key.
    # Because Evennia uses Python's default pickling method, we cannot pass character objects directly into a queue.
    all_objects = ObjectDB.objects.all()
    attacker_queryset = all_objects.filter(db_key=attacker_key)
    attacker = attacker_queryset[0]
    return attacker
