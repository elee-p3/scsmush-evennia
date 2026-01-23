from evennia import default_cmds


class Aspect:
    def __init__(self, name: str, cost: int, custom_name=None):
        self.name = name
        self.cost = cost
        self.custom_name = custom_name

    def __eq__(self, other):
        return self.name.lower() == other.lower()


class LinkedAspect(Aspect):
    def __init__(self, linked_aspect, linked_art, name, cost, custom_name):
        super(Aspect, self).__init__(name, cost, custom_name)
        self.linked_aspect = linked_aspect
        self.linked_art = linked_art


# TODO: CmdEquipAspect
class CmdEquipAspect(default_cmds.MuxCommand):
    key = "+equip"
    aliases = ["equip", "equipaspect", "+equipaspect"]
    locks = "cmd:all()"

    def func(self):
        pass


# TODO: CmdUnequipAspect
class CmdUnequipAspect(default_cmds.MuxCommand):
    key = "+unequip"
    aliases = ["unequip", "unequipaspect", "+unequipaspect"]
    locks = "cmd:all()"

    def func(self):
        pass


# TODO: CmdListAspects
class CmdListAspects(default_cmds.MuxCommand):
    key = "+aspects"
    aliases = ["aspects", "listaspects", "+listaspects"]
    locks = "cmd:all()"

    def func(self):
        pass


# TODO: Character db capacity and max capacity and aspects list. Aspect/Get chargen with Extra Art check code.
# TODO: Aspect/Set equip and unequip. Aspect/list display equipped; aspect/all display equipped and unequipped details.
# TODO: Implement aspect combat functionality. Might be best to do the combat rebalance first before fine-tuning.
# TODO: Modify sheet to display capacity count with colors and fun stuff.
# TODO: Just make all the aspects and test them out one by one!

# VERY LOW COST ASPECTS: 1 Capacity. Expertise and Resistance for specific Hexes.
# TODO: dynamic debuff check: if the requested Aspect on chargen contains "Expertise" or "Resistance", see if it exists, and then
# on apply_debuff() and/or attack obj init, check for relevant Aspects containing "Expertise" or "Resistance"

# LOW COST ASPECTS: 5 Capacity. Expertise and Resistance for standard Debuffs.

# MEDIUM COST ASPECTS: 10 Capacity. Style Aspects like Deflect, etc. ~75 stat Extra Arts. (like a healing potion)
# TODO: redo Aspects model as LinkedAspects to distinguish the table from the rest
deflect = Aspect(name="Deflect", cost=10)

# HIGH COST ASPECTS: 20 Capacity. Self-buffs and crit reacts. ~125 stat Extra Arts. (like a magic wand)

# VERY HIGH COST ASPECTS: 30 Capacity. Aim/Feint/Surge buffs. ~175 stat Extra Arts. (powerful relic)

# EXTREME COST ASPECTS: 40 Capacity. ~225 stat Extra Arts. Admin approval only. (unique artifact)

# List of all Aspects
ASPECTS = [
    deflect
]