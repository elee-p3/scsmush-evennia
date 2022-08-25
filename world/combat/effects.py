class Effect:
    def __init__(self, name: str, ap_cost: int):
        self.name = name
        self.ap_cost = ap_cost

# The following are the list of all selectable "effects" that modify Attacks (specifically, Arts).
# The effects are categorized as modifying the character's current turn or only the next turn.
# The AP Cost of an effect is in addition to the base AP cost of an Art (15, I'm thinking).
# Currently, all persistent effects apply to the attacker, not to the target. We can figure out debuffs later.

# Current Turn Effects

crush = Effect("Crush", 10)
# 1) Lower opponent's block chance. 2) Increase block penalty if blocked.
sweep = Effect("Sweep", 10)
# 1) Lower opponent's dodge chance. 2) Increase chance of Glancing Blow (partial damage) if dodged.
priority = Effect("Priority", 15)
# 1) Lower opponent's interrupt chance. 2) Increase interrupt chance if used as an interrupt.
ex_move = Effect("EX", -15)
# An EX attack costs 0 AP but 100% EX.
rush = Effect("Rush", 5)
# 1) Increase accuracy if not used as interrupt. 2) Decrease all reaction chances until next action.
# This is a hybrid current/next turn effect.

# Next Turn Effects
weave = Effect("Weave", 5)
# 1) Decrease accuracy of this attack. 2) Increase dodge chances until next action.
brace = Effect("Brace", 5)
# 1) Decrease accuracy of this attack. 2) Increase block and endure chances until next action.
bait = Effect("Bait", 5)
# 1) Decrease accuracy of this attack. 2) Increase interrupt chance until next action.

# List of all Effects

EFFECTS = [crush, sweep, priority, ex_move, rush, weave, brace, bait]