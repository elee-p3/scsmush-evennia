def damage_calc(attack_dmg, base_stat, parry, barrier):
    def_stat = 0
    if base_stat == "Power":
        def_stat = parry
    if base_stat == "Knowledge":
        def_stat = barrier
    # return int(int(attack_dmg) / (def_stat/100))
    damage = int(int(attack_dmg) / (def_stat/100))
    return damage


def dodge_calc(attack_acc, speed, sweep_boole, weave_boole):
    accuracy = int(int(attack_acc) / (speed/100))
    # Checking to see if the attack has sweep and improving accuracy/reducing dodge chance if so.
    if sweep_boole:
        accuracy += 10
    # Checking to see if the defender is_weaving and reducing accuracy/improving dodge chance if so.
    if weave_boole:
        accuracy -= 10
    return accuracy


def block_chance_calc(attack_acc, base_stat, speed, parry, barrier, crush_boole, brace_boole):
    def_stat = 0
    if base_stat == "Power":
        def_stat = parry
    if base_stat == "Knowledge":
        def_stat = barrier
    averaged_def = (def_stat + speed)/2
    accuracy = int(int(attack_acc) / (averaged_def/100))
    # Checking to see if the defender is_bracing and reducing accuracy/improving block chance if so.
    if crush_boole:
        accuracy += 10
    if brace_boole:
        accuracy -= 10
    return accuracy


def block_damage_calc(base_damage):
    return base_damage / 2


def ex_gain_on_attack(damage_inflicted, current_ex, max_ex):
    ex_gain = int(damage_inflicted) / 10
    new_ex = current_ex + ex_gain
    if new_ex > max_ex:
        new_ex = max_ex
    return new_ex


def ex_gain_on_defense(damage_taken, current_ex, max_ex):
    ex_gain = int(damage_taken) / 5
    new_ex = current_ex + ex_gain
    if new_ex > max_ex:
        new_ex = max_ex
    return new_ex


def normalize_status(character):
    # This function sets every status effect to default/neutral state.
    character.db.is_aiming = False
    character.db.is_feinting = False
    character.db.is_rushing = False
    character.db.is_weaving = False
    character.db.is_bracing = False
    character.db.is_baiting = False
    character.db.block_penalty = 0


def glancing_blow_calc(dice_roll, accuracy, sweep_boolean=False):
    # If a dodge attempt fails, check if the result was a "glancing blow" instead.
    # For now, a flat value only modified by having "sweep" on an attack. Returns a Boolean.
    diff_between_roll_and_acc = accuracy - dice_roll
    # 10% of glancing blow.
    chance_of_glance = 10
    if sweep_boolean:
        # The Sweep effect increases the chance of a glancing blow to 20%.
        chance_of_glance += 10
    if chance_of_glance >= diff_between_roll_and_acc:
        return True
    return False


def check_for_effects(attack):
    # This function checks for effects on an attack and modifies the attack object accordingly.
    # Modify this function as more effects are implemented.
    modified_attack = attack
    if attack.effects:
        for effect in attack.effects:
            if effect == "Crush":
                modified_attack.has_crush = True
            if effect == "Sweep":
                modified_attack.has_sweep = True
            if effect == "Priority":
                modified_attack.has_priority = True
            if effect == "Rush":
                modified_attack.has_rush = True
            if effect == "Weave":
                modified_attack.has_weave = True
            if effect == "Brace":
                modified_attack.has_brace = True
            if effect == "Bait":
                modified_attack.has_bait = True
    return modified_attack


def combat_tick(character):
    # This function represents a "tick" or the end of a turn. Any "action," like +attack or +pass, counts as a tick.
    # The attack command should cause a tick, then apply any new effects associated with the attack.
    # E.g., if last turn's attack had Brace and this turn's has Weave, tick to remove is_bracing, then apply is_weaving.
    character.db.is_aiming = False
    character.db.is_feinting = False
    character.db.is_rushing = False
    character.db.is_weaving = False
    character.db.is_bracing = False
    character.db.is_baiting = False
    # Currently, reduce block penalty by 10 per tick.
    if character.db.block_penalty > 0:
        if character.db.block_penalty - 10 < 0:
            character.db.block_penalty = 0
        else:
            character.db.block_penalty -= 10
    return character


def apply_attacker_effects(attacker, attack):
    # This function checks for effects on an attack and modifies the attacker's status accordingly.
    # Modify this function as more effects are implemented.
    if attack.effects:
        for effect in attack.effects:
            if effect == "Rush":
                attacker.db.is_rushing = True
            if effect == "Weave":
                attacker.db.is_weaving = True
            if effect == "Brace":
                attacker.db.is_bracing = True
            if effect == "Bait":
                attacker.db.is_baiting = True
    return attacker