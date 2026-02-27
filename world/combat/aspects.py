from evennia import default_cmds
from world.combat.attacks import ActionResult


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


# TODO: Just make all the aspects and test them out one by one!
# TODO: add "Spirited", "Savage", "Moment of Truth", "Nerves of Steel" to status_effects
# Just_perfect_dodged/just_perfect_guarded bools on character

# VERY LOW COST ASPECTS: 1 Capacity. Expertise and Resistance for specific Hexes, and
# LOW COST ASPECTS: 5 Capacity. Expertise and Resistance for standard Debuffs,
# are not stored in the ASPECTS list but instead string-matched to DEBUFFS in +getaspect and apply_debuff().

# MEDIUM COST ASPECTS: 10 Capacity. Style Aspects like Deflect, etc. ~75 stat Extra Arts. (like a healing potion)
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
savage = Aspect(name="Savage", cost=10)
# Spirited: When you suffer a critical hit, gain a temporary boost to accuracy and speed.
spirited = Aspect(name="Spirited", cost=10)

# HIGH COST ASPECTS: 20 Capacity. Self-buffs and crit reacts. ~125 stat Extra Arts. (like a magic wand)
# Counterstrike (Protect)
counterstrike = Aspect(name="Counterstrike", cost=20)
# Counterspell (Reflect)
counterspell = Aspect(name="Counterspell", cost=20)
# Ferocity (Acuity)
ferocity = Aspect(name="Ferocity", cost=20)
# Eagle Eye (Haste)
eagle_eye = Aspect(name="Eagle Eye", cost=20)
# Sleight of Hand (Blink)
sleight_of_hand = Aspect(name="Sleight of Hand", cost=20)
# Self-Mastery (Purity)
self_mastery = Aspect(name="Self-Mastery", cost=20)
# Resilience (Bless)
resilience = Aspect(name="Resilience", cost=20)
# Battle Rage (Berserk+): permanent Berserk state with reduced AP penalty; immune to Berserk
battle_rage = Aspect(name="Battle Rage", cost=20)
# Rock Solid (Petrify+): permanent Petrify state with mitigated dodge penalty; immune to Petrify
rock_solid = Aspect(name="Rock Solid", cost=20)
# Slippery (Slime+): permanent Slime state with mitigated block penalty; immune to Slime
slippery = Aspect(name="Slippery", cost=20)
# Perfect Dodge: similar to MotM's Parry, slightly improve Dodge chances and make crit dodges possible that make
# your next Art more accurate and have no AP cost
perfect_dodge = Aspect(name="Perfect Dodge", cost=20)
# Perfect Guard: similar to MotM's JD, slightly improve Block chances and make crit blocks possible that negate all
# damage and give an immediate flat AP boost
perfect_guard = Aspect(name="Perfect Guard", cost=20)
# Perfect Grit: similar to MotM's Toughness, slightly improve Endure chances and make crit endures possible that negate
# most damage, improve your endure bonus for your next Art, and make your next Art more damaging
perfect_grit = Aspect(name="Perfect Grit", cost=20)
# Perfect Break: when it procs, greatly improve damage mitigation on successful interrupt
perfect_break = Aspect(name="Perfect Break", cost=20)

# VERY HIGH COST ASPECTS: 30 Capacity. Aim/Feint/Surge buffs. ~175 stat Extra Arts. (powerful relic)
# Sniper: Aimed attacks inflict more damage.
sniper = Aspect(name="Sniper", cost=30)
# Duelist: Feinted attacks inflict more damage.
duelist = Aspect(name="Duelist", cost=30)
# Moment of Truth: Using Surge greatly improves your Acc for your next Attack or Interrupt
# Improvement I can add by making it a status effect: sticks around but worse for 2nd turn, used up when succeeds
moment_of_truth = Aspect(name="Moment of Truth", cost=30)
# Nerves of Steel: Using Surge greatly improves your Speed for your next Reaction (same as above?)
nerves_of_steel = Aspect(name="Nerves of Steel", cost=30)

# EXTREME COST ASPECTS: 40 Capacity. ~225 stat Extra Arts. Admin approval only. (unique artifact)

# List of all Aspects
ASPECTS = [
    deflect,
    iron_skin,
    tumble,
    savage,
    spirited,
    counterstrike,
    counterspell,
    ferocity,
    eagle_eye,
    sleight_of_hand,
    self_mastery,
    resilience,
    battle_rage,
    rock_solid,
    slippery,
    perfect_dodge,
    perfect_guard,
    perfect_grit,
    perfect_break,
    sniper,
    duelist,
    moment_of_truth,
    nerves_of_steel
]

# BUFF_EQ dict stores equivalencies between always-on (when-equipped) self-buffing Aspects and the associated buff.
# Buff name string is key and Aspect object is value. This will help to avoid effectively stacking the same buff.
# Includes debuffs with upsides: Berserk, Petrify, and Slime.
BUFF_EQ = {
    "Protect": counterstrike,
    "Reflect": counterspell,
    "Acuity": ferocity,
    "Haste": eagle_eye,
    "Blink": sleight_of_hand,
    "Purity": self_mastery,
    "Bless": resilience,
    "Berserk": battle_rage,
    "Petrify": rock_solid,
    "Slime": slippery
}