from world.scenes.models import Scene, LogEntry
from django.utils.html import escape

def damage_calc(attack_dmg, base_stat, parry, barrier):
    def_stat = 0
    if base_stat == "Power":
        def_stat = parry
    if base_stat == "Knowledge":
        def_stat = barrier
    # return int(int(attack_dmg) / (def_stat/100))
    # damage = int(int(attack_dmg) / (def_stat/100))
    damage = 1.6 * (attack_dmg - def_stat) + 110
    return damage


def modify_accuracy(action, character):
    accuracy = action.acc
    # First, check if this is the attacker's final action, and if so, apply a final action penalty.
    if hasattr(character.db, "final_action"):
        if character.db.final_action:
            accuracy -= 30
    # Then, check if the character has an endure bonus and, if so, apply it.
    if character.db.endure_bonus:
        accuracy += character.db.endure_bonus
    # Check if the character is rushing and, if so, add 7 to accuracy.
    if "Rush" in action.effects:
        accuracy += 7
    return accuracy


def modify_damage(action, character):
    damage = action.dmg
    # Modify attack damage based on base stat.
    if action.base_stat == "Power":
        damage += character.db.power
    if action.base_stat == "Knowledge":
        damage += character.db.knowledge
    return damage


def dodge_calc(attack_acc, speed, sweep_boole, weave_boole, rush_boole):
    # accuracy = int(int(attack_acc) / (speed/100))
    accuracy = 100.0 - (0.475 * (speed - attack_acc) + 10.0)
    # Checking to see if the attack has sweep and improving accuracy/reducing dodge chance if so.
    if sweep_boole:
        accuracy += 10
    # Checking to see if the defender is_rushing and improving accuracy if so.
    if rush_boole:
        accuracy += 5
    # Checking to see if the defender is_weaving and reducing accuracy/improving dodge chance if so.
    if weave_boole:
        accuracy -= 10
    # cap accuracy at 99%
    if accuracy > 99:
        accuracy = 99
    elif accuracy < 1:
        accuracy = 1
    return accuracy


def block_chance_calc(attack_acc, base_stat, speed, parry, barrier, crush_boole, brace_boole, block_penalty, rush_boole):
    def_stat = 0
    if base_stat == "Power":
        def_stat = parry
    if base_stat == "Knowledge":
        def_stat = barrier
    averaged_def = (def_stat + speed)/2 + 50
    # accuracy = int(int(attack_acc) / (averaged_def/100))
    accuracy = 100.0 - (0.475 * (averaged_def - attack_acc))
    # Checking to see if the defender is_bracing and reducing accuracy/improving block chance if so.
    if crush_boole:
        accuracy += 10
    if brace_boole:
        accuracy -= 10
    # Checking to see if the defender is_rushing and improving accuracy if so.
    if rush_boole:
        accuracy += 5
    # Incorporating block penalty.
    accuracy += block_penalty
    if accuracy > 99:
        accuracy = 99
    elif accuracy < 1:
        accuracy = 1
    return accuracy


def endure_chance_calc(attack_acc, base_stat, speed, parry, barrier, brace_boole, rush_boole):
    # Calculate the chance of successfully enduring. Like Block, should be based on both Speed and relevant defense.
    def_stat = 0
    if base_stat == "Power":
        def_stat = parry
    if base_stat == "Knowledge":
        def_stat = barrier
    averaged_def = (def_stat + speed) / 2 + 50
    # accuracy = int(int(attack_acc) / (averaged_def / 100))
    accuracy = 100.0 - (0.475 * (averaged_def - attack_acc))
    # Checking to see if the defender is_bracing and reducing accuracy/improving block chance if so.
    if brace_boole:
        accuracy -= 10
    # Checking to see if the defender is_rushing and improving accuracy if so.
    if rush_boole:
        accuracy += 5
    if accuracy > 99:
        accuracy = 99
    elif accuracy < 1:
        accuracy = 1
    return accuracy


def interrupt_chance_calc(incoming_accuracy, outgoing_accuracy, bait_boole, rush_boole, incoming_priority_boole,
                          outgoing_priority_boole):
    interrupt_chance = 40 + int(outgoing_accuracy) - int(incoming_accuracy)
    if bait_boole:
        interrupt_chance += 10
    if rush_boole:
        interrupt_chance -= 5
    if incoming_priority_boole:
        interrupt_chance -= 15
    if outgoing_priority_boole:
        interrupt_chance += 15
    return interrupt_chance


def interrupt_mitigation_calc(unmitigated_incoming_damage, outgoing_damage):
    # This function mitigates the damage taken by the interrupter on a successful interrupt relative to the Damage
    # of the interrupting attack. This discourages super-high-Accuracy super-low-Damage interrupts.
    mitigated_damage = unmitigated_incoming_damage / 2
    if unmitigated_incoming_damage > outgoing_damage:
        mitigated_damage *= (unmitigated_incoming_damage / outgoing_damage)
    # Check to make sure nothing wacky has happened and the incoming attack isn't doing MORE damage.
    if mitigated_damage > unmitigated_incoming_damage:
        mitigated_damage = unmitigated_incoming_damage
    return mitigated_damage


def endure_bonus_calc(damage_taken):
    # Calculate the accuracy bonus to your next attack from enduring. Should be capped at around 10 to 15.
    accuracy_bonus = int(damage_taken) / 15
    if accuracy_bonus > 12:
        accuracy_bonus = 12
    return accuracy_bonus


def block_damage_calc(base_damage, block_penalty):
    mitigated_damage = base_damage / 2
    # Modify the base mitigated damage by the block penalty.
    # Currently, a doubled percentage increase: e.g., if someone successfully blocks with a 20 block penalty,
    # first halve the damage, then multiply that by x1.4.
    if block_penalty > 0:
        mitigated_damage *= ((block_penalty * 2) / 100 + 1)
    # Make sure that this can't somehow do more damage than a failed block.
    if mitigated_damage > base_damage:
        mitigated_damage = base_damage
    return mitigated_damage


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
    character.db.final_action = False
    character.db.KOed = False
    character.db.endure_bonus = 0


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
    # Update 9-7-22: Combat_tick no longer sets Aim or Feint to False. This was preempting their application to +attack.
    # Instead, Aim and Feint are set false at the end of the +attack command itself.
    character.db.is_rushing = False
    character.db.is_weaving = False
    character.db.is_bracing = False
    character.db.is_baiting = False
    character.db.endure_bonus = 0
    # Currently, reduce block penalty per tick by 10 or a third, whichever is higher.
    if character.db.block_penalty > 0:
        if (character.db.block_penalty / 3) > 10:
            block_penalty_reduction = character.db.block_penalty / 3
        else:
            block_penalty_reduction = 10
        if block_penalty_reduction - 10 < 0:
            character.db.block_penalty = 0
        else:
            character.db.block_penalty -= block_penalty_reduction
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


def accrue_block_penalty(character, pre_block_damage, block_boole, crush_boole):
    # If the block succeeds, accrue full block penalty. If the block fails, accrue a minor block penalty.
    # Crush makes the block penalty a lot worse if you block and a little worse if you fail to block.
    if block_boole:
        if crush_boole:
            character.db.block_penalty += (pre_block_damage / 5)
        else:
            character.db.block_penalty += (pre_block_damage / 15)
    else:
        if crush_boole:
            character.db.block_penalty += (pre_block_damage / 15)
        else:
            character.db.block_penalty += (pre_block_damage / 30)
    return character.db.block_penalty


def final_action_check(character):
    # After any reaction in which the character takes damage, check if their LF has dropped to 0 or below.
    if character.db.lf <= 0:
        character.db.final_action = True
        character.msg("You have been reduced to 0 LF or below. Your next action will be your last. Any attacks will"
                      " suffer a penalty to your accuracy.")
    return character


def combat_log_entry(caller, logstring):
    # This function is called when adding "<COMBAT>" messages to the autologger, so that people reading logs of combat
    # scenes can contextualize the RP with the blow-by-blow record of fights.
    if caller.location.db.active_event:
        scene = Scene.objects.get(pk=caller.location.db.event_id)
        scene.addLogEntry(LogEntry.EntryType.COMBAT, escape(logstring), caller)