from world.combat.effects import AimOrFeint
from world.utilities.utilities import find_attacker_from_key
from enum import Enum


class Attack:
    # This is the attack object as stored in individual lists of Arts or in the universal list of Normals.
    def __init__(self, name: str, ap: int, dmg: int, acc: int, base_stat="", effects=""):
        self.name = name # make case-insensitive
        self.ap = ap
        self.dmg = dmg
        self.acc = acc
        self.stat = base_stat
        self.effects = effects

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name.lower() == other.lower()
        elif isinstance(other, Attack):
            return self.name.lower() == other.name.lower()


class AttackDuringAction:
    # This is the parent class for attacks with metadata. Attackers may use either CmdAttack or CmdInterrupt to
    # use their Attacks. CmdAttack must pass an AttackToQueue into the defender's queue so that the defender may
    # choose a reaction. CmdInterrupt is not passed into the defender's queue and resolves without a reaction.
    # Metadata required for both CmdAttack and CmdInterrupt and relevant combat_functions is thus stored here.
    def __init__(self, attack, attacker_key, switches):
        self.attack = attack
        self.attacker_key = attacker_key
        attacker = find_attacker_from_key(attacker_key)
        self.modifier = ""
        self.switches_string = "".join(switches)
        self.has_acuity = False
        self.has_vigor = False
        self.has_bird = False
        self.has_frog = False
        self.has_injure = False
        self.has_pig = False
        self.has_pumpkin = False
        self.has_berserk = False
        self.has_muddle = False
        self.has_strain = False
        self.is_wild = False
        if attacker.db.buffs["Acuity"] > 0:
            self.has_acuity = True
        if attacker.db.buffs["Vigor"] > 0:
            self.has_vigor = True
        if attacker.db.debuffs_transform["Bird"] > 0:
            self.has_bird = True
        if attacker.db.debuffs_transform["Frog"] > 0:
            self.has_frog = True
        if attacker.db.debuffs_transform["Pig"] > 0:
            self.has_pig = True
        if attacker.db.debuffs_transform["Pumpkin"] > 0:
            self.has_pumpkin = True
        if attacker.db.debuffs_standard["Injure"] > 0:
            self.has_injure = True
        if attacker.db.debuffs_standard["Muddle"] > 0:
            self.has_muddle = True
        if attacker.db.debuffs_standard["Berserk"] > 0:
            self.has_berserk = True
        if self.switches_string:
            switches_list = self.switches_string.split()
            for switch in switches_list:
                if switch.lower() == "wild":
                    # This will be checked by critical_hits. Wild attacks are more likely to crit.
                    self.is_wild = True
                    # Wild attacks have -20 accuracy.
                    self.attack.acc -= 20
        if attack.effects:
            split_effects = attack.effects.split()
            for effect in split_effects:
                if effect == "Strain":
                    self.has_strain = True


class AttackToQueue(AttackDuringAction):
    # This is a class that contains an instance of an Attack (see above) as well as the attacker, an ID in the target's
    # queue, and an enum representing if the attacker was Aiming, Feinting, or neither.
    def __init__(self, new_id, attack, attacker_key, aim_or_feint, switches):
        super(AttackToQueue, self).__init__(attack, attacker_key, switches)
        self.id = new_id
        # self.target = target
        self.aim_or_feint = aim_or_feint
        if aim_or_feint == AimOrFeint.AIM:
            self.modifier = "Aimed "
        if aim_or_feint == AimOrFeint.FEINT:
            self.modifier = "Feinting "
        # Apply the effects of the attack in the attacker's list to the attack instance so that the defender can
        # check the attack instance for modifiers without needing to access the attacker's status, which may change.
        # Add to this list as new Effects are introduced.
        self.has_crush = False
        self.has_sweep = False
        self.has_priority = False
        self.has_rush = False
        self.has_weave = False
        self.has_brace = False
        self.has_bait = False
        self.has_ranged = False
        if attack.effects:
            split_effects = attack.effects.split()
            for effect in split_effects:
                if effect == "Crush":
                    self.has_crush = True
                if effect == "Sweep":
                    self.has_sweep = True
                if effect == "Priority":
                    self.has_priority = True
                if effect == "Rush":
                    self.has_rush = True
                if effect == "Weave":
                    self.has_weave = True
                if effect == "Brace":
                    self.has_brace = True
                if effect == "Bait":
                    self.has_bait = True
                if effect == "Long-Range":
                    self.has_ranged = True


# Enumerate possible attack results to pass into the damage message string function
class ActionResult(Enum):
    REACT_CRIT_FAIL = 1
    REACT_FAIL = 2
    GLANCING_BLOW = 3
    DODGE_SUCCESS = 4
    BLOCK_SUCCESS = 5
    ENDURE_SUCCESS = 6
    INTERRUPT_CRIT_FAIL = 7
    INTERRUPT_FAIL = 8
    INTERRUPT_SUCCESS = 9
    INTERRUPT_CRIT_SUCCESS = 10