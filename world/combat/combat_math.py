def damage_calc(attack_dmg, base_stat, parry, barrier):
    def_stat = 0
    if base_stat == "Power":
        def_stat = parry
    if base_stat == "Knowledge":
        def_stat = barrier
    # return int(int(attack_dmg) / (def_stat/100))
    damage = int(int(attack_dmg) / (def_stat/100))
    return damage


def dodge_calc(attack_acc, speed):
    return int(int(attack_acc) / (speed/100))


def block_chance_calc(attack_acc, base_stat, speed, parry, barrier):
    def_stat = 0
    if base_stat == "Power":
        def_stat = parry
    if base_stat == "Knowledge":
        def_stat = barrier
    averaged_def = (def_stat + speed)/2
    return int(int(attack_acc) / (averaged_def/100))


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
