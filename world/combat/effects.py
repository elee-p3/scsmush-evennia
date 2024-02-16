from enum import Enum

class AimOrFeint(Enum):
    AIM = 1
    FEINT = 2
    NEUTRAL = 3

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
drain = Effect("Drain", -20, "DRN")
# If an attack is not dodged, the attacker heals themselves proportionally to the damage they inflict.
# Note that this healing counts toward the attacker's per-fight healing limit.

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

# List of all Effects

EFFECTS = [crush, sweep, priority, ex_move, rush, weave, brace, bait, heal, revive, drain, regen, vigor]

# Lists of Support and Debuff Effects, Specifically, for Dispel/Cure/Serendipity/Curse/Etc.

SUPPORT = [regen, vigor]
DEBUFFS_STANDARD = []
DEBUFFS_TRANSFORMATION = []
DEBUFFS_HEXES = []
