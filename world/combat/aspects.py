class Aspect:
    def __init__(self, name: str, cost: int, linked_art=None, custom_name=None):
        self.name = name
        self.cost = cost
        self.linked_art = linked_art
        self.custom_name = custom_name

    def __eq__(self, other):
        return self.name.lower() == other.lower()

# TODO: Character db capacity and max capacity and aspects list. Aspect/Get chargen with Extra Art check code.
# TODO: Aspect/Set equip and unequip. Aspect/list display equipped; aspect/all display equipped and unequipped details.
# TODO: Implement aspect combat functionality. Might be best to do the combat rebalance first before fine-tuning.
# TODO: Modify sheet to display capacity count with colors and fun stuff.
# TODO: Just make all the aspects and test them out one by one!

# VERY LOW COST ASPECTS: 5 Capacity. Expertise and Resistance for Hexes; ~70 stat Extra Arts.

# LOW COST ASPECTS: 10 Capacity. Style Aspects like Deflect, etc. ~90 stat Extra Arts.

# MEDIUM COST ASPECTS: 15 Capacity. Expertise and Resistance for standard Debuffs; ~110 stat Extra Arts.

# HIGH COST ASPECTS: 20 Capacity. Self-buffs and crit reacts. ~130 stat Extra Arts.

# VERY HIGH COST ASPECTS: 30 Capacity. Aim/Feint buffs. ~170 stat Extra Arts.

# EXTREME COST ASPECTS: 40 Capacity. ~210 stat Extra Arts. Admin approval only.