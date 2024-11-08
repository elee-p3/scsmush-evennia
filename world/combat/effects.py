from enum import Enum

class AimOrFeint(Enum):
    AIM = 1
    FEINT = 2
    NEUTRAL = 3
    HASTED_AIM = 4
    BLINKED_FEINT = 5

class Effect:
    def __init__(self, name: str, ap: int, abbr: str):
        self.name = name
        self.ap = ap
        self.abbreviation = abbr

    def __eq__(self, other):
        return self.name.lower() == other.lower()

# The following are the list of all selectable "effects" that modify Attacks (specifically, Arts).
# The effects are categorized as modifying the character's current turn or only the next turn.
# The AP Cost of an effect is in addition to the base AP cost of an Art (15, I'm thinking).
# Currently, all persistent effects apply to the attacker, not to the target. We can figure out debuffs later.

# IMPORTANT NOTE: if you add a new Effect, add it to at_pre_puppet in characters.py and normalize_status and combat_tick
# in combat_functions.py.

# Attack Enhancers

crush = Effect("Crush", -10, "CRU")
# 1) Lower opponent's block chance. 2) Increase block penalty if blocked.
sweep = Effect("Sweep", -10, "SWP")
# 1) Lower opponent's dodge chance. 2) Increase chance of Glancing Blow (partial damage) if dodged.
priority = Effect("Priority", -15, "PRI")
# 1) Lower opponent's interrupt chance. 2) Increase interrupt chance if used as an interrupt.
ex_move = Effect("EX", 5, "EX")
# An EX attack costs 0 AP but 100% EX.
rush = Effect("Rush", -5, "RSH")
# 1) Increase accuracy if not used as interrupt. 2) Decrease all reaction chances until next action.
# This is a hybrid Attack Enhancer / Reaction Modifier.
long_range = Effect("Long-Range", -10, "RNGD")
# This attack is harder to interrupt with non-Ranged attacks and, if not dodged or interrupted, inflicts a "knockback"
# accuracy penalty to the target until their next action. In exchange, slightly decrease both the attack's accuracy and
# all the attacker's reaction chances until next action.
# This is also a hybrid Attack Enhancer / Reaction Modifier.
drain = Effect("Drain", -20, "DRN")
# If an attack is not dodged, the attacker heals themselves proportionally to the damage they inflict.
# Note that this healing counts toward the attacker's per-fight healing limit.
dispel = Effect("Dispel", -10, "DIS")
# If the attack is successful or endured, remove one random buff from the target.
strain = Effect("Strain", -5, "STR")
# Damage oneself in exchange for inflicting more damage on a successful hit, relative to the AP cost of the action.

# Reaction Modifiers

weave = Effect("Weave", -5, "WV")
# 1) Decrease accuracy of this attack. 2) Increase dodge chances until next action.
brace = Effect("Brace", -5, "BRC")
# 1) Decrease accuracy of this attack. 2) Increase block and endure chances until next action.
bait = Effect("Bait", -5, "BT")
# 1) Decrease accuracy of this attack. 2) Increase interrupt chance until next action.

# Healing and Support

heal = Effect("Heal", -10, "HEAL")
# This Art heals instead of doing damage and is subject to heal depreciation.
revive = Effect("Revive", -15, "REV")
# This healing Art, when used on a KOed ally, eliminates their 1-turn inaction penalty on being healed.
regen = Effect("Regen", -15, "REGEN")
# Applies the Regen Effect: Heal the target over time. This healing counts toward the target's per-fight healing limit.
vigor = Effect("Vigor", -15, "VGR")
# Applies the Vigor Effect: Increase Power and Knowledge.
protect = Effect("Protect", -15, "PRT")
# Applies the Protect Effect: Slightly increase Parry and improve damage mitigation when interrupting Power-type
# attacks, significantly when the interrupt is successful and moderately when it fails.
reflect = Effect("Reflect", -15, "REFL")
# Applies the Reflect Effect: Slightly increase Barrier and improve damage mitigation when interrupting Knowledge-type
# attacks, significantly when the interrupt is successful and moderately when it fails.
acuity = Effect("Acuity", -15, "ACU")
# Applies the Acuity Effect: Slightly increase Speed and significantly improve chance of critical hits.
haste = Effect("Haste", -15, "HST")
# Applies the Haste Effect: Slightly increase Speed and improve the effectiveness of the Aim command.
blink = Effect("Blink", -15, "BNK")
# Applies the Blink Effect: Slightly increase Speed and improve the effectiveness of the Feint command.
serendipity = Effect("Serendipity", -10, "SER")
# Applies a random effect from BUFFS.
bless = Effect("Bless", -15, "BLS")
# Applies the Bless Effect: Increase resistance to all Debuffs.
purity = Effect("Purity", -15, "PUR")
# Applies the Purity Effect: Grant immunity to all non-Standard Debuffs, i.e., Transformation and Hexes.
cure = Effect("Cure", -10, "CURE")
# Removes a random debuff, or a specific debuff with the switch "heal/[name of debuff]". Heal is an alias of CmdAttack.

# Debuffs (Standard)

poison = Effect("Poison", -15, "POI")
# Applies the Poison Effect: Inflicts damage over time.
wound = Effect("Wound", -15, "WND")
# Applies the Wound Effect: Whenever this character acts, inflict damage relative to the AP cost of their action.
# Actions with an AP cost of 0 or less do not inflict damage.
curse = Effect("Curse", -15, "CRS")
# Applies the Curse Effect: Decrease a target's resistance to all debuffs.
injure = Effect("Injure", -15, "INJ")
# Applies the Injure Effect: Lower the target's Power and Parry and slightly lower Speed.
muddle = Effect("Muddle", -15, "MDL")
# Applies the Muddle Effect: Lower the target's Knowledge and Barrier and slightly lower Speed.
miasma = Effect("Miasma", -15, "MSM")
# Applies the Miasma Effect: Halves the effectiveness of heals on the target.
berserk = Effect("Berserk", -15, "BSK")
# Applies the Berserk Effect: Increase the target's Power, Knowledge, and Speed but prevent them from using any Arts
# below a Force of 50, thus requiring them to use attacks of lower Accuracy.
petrify = Effect("Petrify", -15, "PTR")
# Applies the Petrify Effect: Lower a target's Speed and greatly reduce their Dodge chance specifically, but somewhat
# improve their Block and Endure chances.
slime = Effect("Slime", -15, "SLM")
# Applies the Slime Effect: Lower a target's Speed and greatly reduce their Block chance specifically, but somewhat
# improve their Dodge and Endure chances.

# Debuffs (Transformation)

# Transformation debuffs have dramatic effects but serious limitations. First, they only last for 2 rounds. Second,
# a target can only be affected by one Transformation debuff at a time. Third, being affected by a Transformation
# debuff greatly increases the target's resistance to any future Transformation attempts during the fight. Finally,
# these debuffs have the highest AP costs of any Effects.

morph = Effect("Morph", -25, "MRPH")
# Inflict a random Transformation Effect.
bird = Effect("Bird", -35, "BIRD")
# Turn the target into a bird, effectively halving their Power and Parry.
frog = Effect("Frog", -35, "FROG")
# Turn the target into a frog, effectively halving their Power and Barrier.
pig = Effect("Pig", -35, "PIG")
# Turn the target into a pig, effectively halving their Knowledge and Parry.
pumpkin = Effect("Pumpkin", -35, "PMKN")
# Turn the target into a pumpkin, effectively halving their Knowledge and Barrier. Somehow, they can still hop around.

# Debuffs (Hexes)

# Mechanically, all Hexes cost 10 AP and have the same Distraction effect, persisting for 3 actions: they moderately
# reduce the target's reaction chances multiplied by the number of different Hexes on the target. Being Hexed also
# moderately increases the target's resistance to being Hexed again during the fight, a bonus which depreciates with
# each action. [Even though they're all the same, I want players to be able to pick a single one to inflict, so I'm
# going to make them distinct Effects.]

hex1 = Effect("Hex1", -10, "HEX1")
hex2 = Effect("Hex2", -20, "HEX2")
hex3 = Effect("Hex3", -30, "HEX3")
# Inflict X number of random Hexes.
blind = Effect("Blind", -10, "BLN")
silence = Effect("Silence", -10, "SLN")
amnesia = Effect("Amnesia", -10, "AMN")
sleep = Effect("Sleep", -10, "SLP")
charm = Effect("Charm", -10, "CHR")
confuse = Effect("Confuse", -10, "CNF")
fear = Effect("Fear", -10, "FR")
bind = Effect("Bind", -10, "BND")
zombie = Effect("Zombie", -10, "ZMB")
doom = Effect("Doom", -10, "DM")
dance = Effect("Dance", -10, "DNC")
stinky = Effect("Stinky", -10, "STN")
itchy = Effect("Itchy", -10, "ITC")
old = Effect("Old", -10, "OLD")

# List of all Effects

EFFECTS = [crush,
           sweep,
           priority,
           ex_move,
           rush,
           weave,
           brace,
           bait,
           heal,
           revive,
           drain,
           regen,
           vigor,
           dispel,
           long_range,
           protect,
           reflect,
           acuity,
           haste,
           blink,
           serendipity,
           poison,
           bless,
           wound,
           curse,
           injure,
           muddle,
           miasma,
           berserk,
           petrify,
           slime,
           morph,
           bird,
           frog,
           pig,
           pumpkin,
           hex1,
           hex2,
           hex3,
           blind,
           silence,
           amnesia,
           sleep,
           charm,
           confuse,
           fear,
           bind,
           zombie,
           doom,
           dance,
           stinky,
           itchy,
           old,
           purity,
           cure,
           strain]

# Lists of Support and Debuff Effects, Specifically, for Dispel/Cure/Serendipity/Curse/Etc.
# SUPPORT are flags that must be accompanied by Heal. BUFFS are options for random selection, e.g., Serendipity, Dispel.

SUPPORT = [revive,
           serendipity,
           cure,
           regen,
           vigor,
           protect,
           reflect,
           acuity,
           haste,
           blink,
           bless,
           purity]
BUFFS = SUPPORT[3:]
DEBUFFS_STANDARD = [poison,
                    wound,
                    curse,
                    injure,
                    muddle,
                    miasma,
                    berserk,
                    petrify,
                    slime]
DEBUFFS_TRANSFORMATION = [bird,
                          frog,
                          pig,
                          pumpkin]
DEBUFFS_HEXES = [blind,
                 silence,
                 amnesia,
                 sleep,
                 charm,
                 confuse,
                 fear,
                 bind,
                 zombie,
                 doom,
                 dance,
                 stinky,
                 itchy,
                 old]
DEBUFFS = DEBUFFS_STANDARD + DEBUFFS_TRANSFORMATION + DEBUFFS_HEXES

