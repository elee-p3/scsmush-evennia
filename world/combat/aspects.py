from evennia import default_cmds


class Aspect:
    def __init__(self, name: str, cost: int, custom_name=""):
        self.name = name
        self.cost = cost
        self.custom_name = custom_name

    def __eq__(self, other):
        if isinstance(other, Aspect):
            return self.name.lower() == other.name.lower()

        elif isinstance(other, str):
            return self.name.lower() == other.lower()


class LinkedAspect(Aspect):
    def __init__(self, linked_aspect, linked_art, name, cost, custom_name):
        super(Aspect, self).__init__(name, cost, custom_name)
        self.linked_aspect = linked_aspect
        self.linked_art = linked_art


# TODO: Character db capacity and max capacity and aspects list. Aspect/Get chargen with Extra Art check code.
# TODO: Aspect/Set equip and unequip. Aspect/list display equipped; aspect/all display equipped and unequipped details.
# TODO: Implement aspect combat functionality. Might be best to do the combat rebalance first before fine-tuning.
# TODO: Modify sheet to display capacity count with colors and fun stuff.
# TODO: Just make all the aspects and test them out one by one!

# VERY LOW COST ASPECTS: 1 Capacity. Expertise and Resistance for specific Hexes, and
# LOW COST ASPECTS: 5 Capacity. Expertise and Resistance for standard Debuffs,
# are not stored in the ASPECTS list but instead string-matched to DEBUFFS in +getaspect and apply_debuff().

# MEDIUM COST ASPECTS: 10 Capacity. Style Aspects like Deflect, etc. ~75 stat Extra Arts. (like a healing potion)
# TODO: redo Aspects model as LinkedAspects to distinguish the table from the rest
# Deflect: Blocking mitigation improves based on Speed. The more evasive you are, the less damage you take when
# successfully blocking.
deflect = Aspect(name="Deflect", cost=10)
# Iron Skin: Glancing Blow dodge chance improves based on defense (Parry/Barrier). The sturdier you are, the more
# likely you are to partially negate an attack when you dodge.
iron_skin = Aspect(name="Iron Skin", cost=10)
# Tumble: Endure accuracy bonus improves based on Speed. The more evasive you are, the more you benefit from choosing
# to endure an attack.
tumble = Aspect(name="Tumble", cost=10)
# Breakthrough: Higher-damage attacks are somewhat harder to interrupt than they would otherwise be. This effect is not
# hidden to the interrupter.
# Saboteur: All standard debuff (i.e., neither transformations nor hexes) chances improve and debuff AP costs slightly
# decrease, but all targets gain more EX when hit with attempted debuffs.
# Synergist: Buff AP costs decrease, but all attackers gain more EX when they hit you.
# Tactician: Reaction Modifier Effect AP costs decrease (to 0 in many cases), but Arts with Reaction Modifier Effects
# generate significantly less EX from attacking.
# Marauder: Attack Enhancer Effect AP costs decrease, but Arts with Attack Enhancer Effects are slightly less accurate.
# Bewitching: Hexes and Transformation debuffs specifically are harder to resist and the latter cost less AP.
# Vengeful: Your base critical hit chance is lower, but increases as your health decreases.
# Reckless: Your base critical hit chance is higher, but you are also more likely to suffer critical hits.
# Savage: When you inflict a critical hit, gain a temporary boost to accuracy and speed.
# Spirited: When you suffer a critical hit, gain a temporary boost to accuracy and speed.

# HIGH COST ASPECTS: 20 Capacity. Self-buffs and crit reacts. ~125 stat Extra Arts. (like a magic wand)
# TODO: have apply_buff() check for redundant aspect and note that only a Speed buff will be applied?
# Counterstrike (Protect)
# Counterspell (Reflect)
# Ferocity (Acuity)
# Eagle Eye (Haste)
# Sleight of Hand (Blink)
# Self-Mastery (Purity)
# Resilience (Bless)
# Battle Rage (Berserk+): permanent Berserk state with reduced AP penalty; immune to Berserk
# [may do the same for Slime and Petrify as I do for Berserk here?]
# Perfect Dodge: similar to MotM's Parry, slightly improve Dodge chances and make crit dodges possible that make
# your next Art more accurate and have no AP cost
# Perfect Guard: similar to MotM's JD, slightly improve Block chances and make crit blocks possible that negate all
# damage and give an immediate AP boost
# Perfect Grit: similar to MotM's Toughness, slightly improve Endure chances and make crit endures possible that negate
# most damage, improve your endure bonus for your next Art, and make your next Art more damaging
# May do the same for interrupt? Perfect Break?

# VERY HIGH COST ASPECTS: 30 Capacity. Aim/Feint/Surge buffs. ~175 stat Extra Arts. (powerful relic)
# TODO: add CmdSurge and make Aim/Feint cost no AP to encourage using mechanics
# Sniper: Aimed attacks inflict more damage.
# Duelist: Feinted attacks inflict more damage.
# ~~~: Using Surge greatly improves your Acc for your next Attack or Interrupt (diminishing returns til proc?)
# Nerves of Steel: Using Surge greatly improves your Speed for your next Reaction (same as above?)

# EXTREME COST ASPECTS: 40 Capacity. ~225 stat Extra Arts. Admin approval only. (unique artifact)

# List of all Aspects
ASPECTS = [
    deflect,
    iron_skin,
    tumble
]