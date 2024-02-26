from enum import Enum

class AimOrFeint(Enum):
    AIM = 1
    FEINT = 2
    NEUTRAL = 3
    HASTED_AIM = 4
    BLINKED_FEINT = 5

class Effect:
    def __init__(self, name: str, ap_change: int, abbr: str):
        self.name = name
        self.ap_change = ap_change
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

# Debuffs (Standard)

poison = Effect("Poison", -15, "POI")
# Applies the Poison Effect: Inflicts damage over time.

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
           bless]

# Lists of Support and Debuff Effects, Specifically, for Dispel/Cure/Serendipity/Curse/Etc.
# SUPPORT are flags that must be accompanied by Heal. BUFFS are options for random selection, e.g., Serendipity, Dispel.

SUPPORT = [revive,
           serendipity,
           regen,
           vigor,
           protect,
           reflect,
           acuity,
           haste,
           blink,
           bless]
BUFFS = SUPPORT[2:]
DEBUFFS_STANDARD = [poison]
DEBUFFS_TRANSFORMATION = []
DEBUFFS_HEXES = []
DEBUFFS = DEBUFFS_STANDARD + DEBUFFS_TRANSFORMATION + DEBUFFS_HEXES

