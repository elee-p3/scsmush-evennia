from world.combat.effects import AimOrFeint


class Attack:
    # This is the attack object as stored in individual lists of Arts or in the universal list of Normals.
    def __init__(self, name: str, ap_change: int, dmg: int, acc: int, base_stat="", effects=[]):
        self.name = name # make case-insensitive
        self.ap_change = ap_change
        self.dmg = dmg
        self.acc = acc
        self.base_stat = base_stat
        self.effects = effects

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name.lower() == other.lower()
        elif isinstance(other, Attack):
            return self.name.lower() == other.name.lower()


class AttackInstance:
    # This is a class that contains an instance of an Attack (see above) as well as the attacker, an ID in the target's
    # queue, and an enum representing if the attacker was Aiming, Feinting, or neither.
    def __init__(self, new_id, attack, attacker_key, aim_or_feint):
        self.id = new_id
        # self.target = target
        self.attack = attack
        self.attacker_key = attacker_key
        self.aim_or_feint = aim_or_feint
        self.modifier = ""
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
        if attack.effects:
            for effect in attack.effects:
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
        # TODO: To avoid getting in a pickle, 1) don't put target in AttackInstance, but just keep it in the attack
        # command, and 2) only send the attacker's key and then add a function to find the attacker using its key.

    # def __deepcopy__(self, memodict={}):
    #     return AttackInstance(self.target, self.attack, self.attacker, self.aim_or_feint)
    #
    # def __str__(self):
    #     return ""