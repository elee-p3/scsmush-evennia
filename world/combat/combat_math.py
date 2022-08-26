def damage_calc(attack_dmg, base_stat, parry, barrier):
    def_stat = 0
    if base_stat == "Power":
        def_stat = parry
    if base_stat == "Knowledge":
        def_stat = barrier
    return int(int(attack_dmg) / (def_stat/100))


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