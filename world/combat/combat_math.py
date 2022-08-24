def damage_calc(attack_dmg, base_stat, parry, barrier):
    def_stat = 0
    if base_stat == "Power":
        def_stat = parry
    if base_stat == "Knowledge":
        def_stat = barrier
    return int(attack_dmg / (def_stat/100))


def dodge_calc(attack_acc, speed):
    return int(attack_acc / (speed/100))
