from world.scenes.models import Scene, LogEntry
from django.utils.html import escape
from evennia.objects.models import ObjectDB
import random
import math
from world.utilities.utilities import logger
from world.combat.attacks import Attack
from world.combat.effects import BUFFS, DEBUFFS, AimOrFeint


def assign_attack_instance_id(target):
    # Checks the defender's queue in order to determine the ID number of the new incoming attack instance.
    if not target.db.queue:
        last_id = 0
    else:
        last_id = max((attack.id for attack in target.db.queue))
    new_id = last_id + 1
    return new_id


def find_attacker_from_key(attacker_key):
    # This finds the attacker's character object from their key.
    # Because Evennia uses Python's default pickling method, we cannot pass character objects directly into a queue.
    all_objects = ObjectDB.objects.all()
    attacker_queryset = all_objects.filter(db_key=attacker_key)
    attacker = attacker_queryset[0]
    return attacker


def damage_calc(attack_dmg, attacker_stat, base_stat, defender):
    def_stat = 0
    if base_stat == "Power":
        def_stat = defender.db.parry
    if base_stat == "Knowledge":
        def_stat = defender.db.barrier
    if def_stat == defender.db.parry:
        if defender.db.buffs["Protect"] > 0:
            def_stat += 10
        if defender.db.debuffs["Injure"][0] > 0:
            def_stat -= 10
    if def_stat == defender.db.barrier:
        if defender.db.buffs["Reflect"] > 0:
            def_stat += 10
        if defender.db.debuffs["Muddle"][0] > 0:
            def_stat -= 10
    # Now magnify or mitigate the stat multiplier depending on how different they are.
    # This works OK, but is a placeholder for a more complex curve that I want to implement eventually.
    defender_advantage = def_stat - attacker_stat
    stat_mitigation = def_stat * (-0.00188 * defender_advantage + 1.05)
    damage = 1.85 * attack_dmg - stat_mitigation
    if damage < 0:
        damage = 0
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
    if "Long-Range" in action.effects:
        accuracy -= 5
    return accuracy


def modify_damage(action, character):
    damage = action.dmg
    # Modify attack damage based on base stat.
    if action.stat.lower() == "power":
        base_stat = character.db.power
        # Check for Injure.
        if character.db.debuffs["Injure"][0] > 0:
            base_stat -= 10
        # Check for Berserk.
        if character.db.debuffs["Berserk"][0] > 0:
            base_stat += 10
    if action.stat.lower() == "knowledge":
        base_stat = character.db.knowledge
        # Check for Muddle.
        if character.db.debuffs["Muddle"][0] > 0:
            base_stat -= 10
        # Check for Berserk.
        if character.db.debuffs["Berserk"][0] > 0:
            base_stat += 10
    # Check for Vigor buff.
    base_stat = vigor_check(character, base_stat)

    damage_multiplier = (0.00583 * damage) + 0.708
    total_damage = (damage + base_stat) * damage_multiplier
    return total_damage


def modify_speed(speed, defender):
    # A function to nest within the reaction functions to soften the effects of low and high Speed.
    speed_multiplier = speed * -0.00221 + 1.25
    # Check here for the Acuity buff.
    if defender.db.buffs["Acuity"] > 0:
        speed += 5
    if defender.db.buffs["Haste"] > 0:
        speed += 5
    if defender.db.buffs["Blink"] > 0:
        speed += 5
    if defender.db.debuffs["Injure"][0] > 0:
        speed -= 5
    if defender.db.debuffs["Muddle"][0] > 0:
        speed -= 5
    if defender.db.debuffs["Berserk"][0] > 0:
        speed += 5
    if defender.db.debuffs["Petrify"][0] > 0:
        speed -= 10
    effective_speed = speed * speed_multiplier
    return effective_speed


def dodge_calc(defender, attack_instance):
    # accuracy = int(int(attack_acc) / (speed/100))
    speed = defender.db.speed
    attack_acc = attack_instance.attack.acc
    accuracy = 100.0 - (0.475 * (modify_speed(speed, defender) - attack_acc) + 5)
    # Checking to see if the attack has sweep and improving accuracy/reducing dodge chance if so.
    if attack_instance.has_sweep:
        accuracy += 10
    # Checking to see if the defender is_rushing and improving accuracy if so.
    if defender.db.is_rushing:
        accuracy += 5
    # Checking to see if the defender is_weaving and reducing accuracy/improving dodge chance if so.
    if defender.db.is_weaving:
        accuracy -= 10
    # Checking to see if the defender used_ranged and improving accuracy if so.
    if defender.db.used_ranged:
        accuracy += 5
    # Checking to see if the defender is Petrified and improving accuracy if so.
    if defender.db.debuffs["Petrify"][0] > 0:
        accuracy += 12
    # cap accuracy at 99%
    if accuracy > 99:
        accuracy = 99
    elif accuracy < 1:
        accuracy = 1
    return accuracy


def block_chance_calc(defender, attack_instance):
    def_stat = 0
    if attack_instance.attack.stat == "Power":
        def_stat = defender.db.parry
    if attack_instance.attack.stat == "Knowledge":
        def_stat = defender.db.barrier
    speed = defender.db.speed
    attack_acc = attack_instance.attack.acc
    averaged_def = modify_speed(speed, defender) + def_stat*.5
    # accuracy = int(int(attack_acc) / (averaged_def/100))
    accuracy = 100.0 - (0.475 * (averaged_def - attack_acc))
    # Checking to see if the defender is_bracing and reducing accuracy/improving block chance if so.
    if attack_instance.has_crush:
        accuracy += 10
    if defender.db.is_bracing:
        accuracy -= 10
    # Checking to see if the defender is_rushing and improving accuracy if so.
    if defender.db.is_rushing:
        accuracy += 5
    # Checking to see if the defender used_ranged and improving accuracy if so.
    if defender.db.used_ranged:
        accuracy += 5
    # Checking to see if the defender is Petrified and reducing accuracy if so.
    if defender.db.debuffs["Petrify"][0] > 0:
        accuracy -= 12
    # Incorporating block penalty.
    accuracy += defender.db.block_penalty
    if accuracy > 99:
        accuracy = 99
    elif accuracy < 1:
        accuracy = 1
    return accuracy


def endure_chance_calc(defender, attack_instance):
    # Calculate the chance of successfully enduring. Like Block, should be based on both Speed and relevant defense.
    def_stat = 0
    if attack_instance.attack.stat == "Power":
        def_stat = defender.db.parry
    if attack_instance.attack.stat == "Knowledge":
        def_stat = defender.db.barrier
    speed = defender.db.speed
    attack_acc = attack_instance.attack.acc
    averaged_def = modify_speed(speed, defender) + def_stat*.5
    # accuracy = int(int(attack_acc) / (averaged_def / 100))
    accuracy = 100.0 - (0.475 * (averaged_def - attack_acc))
    # Checking to see if the defender is_bracing and reducing accuracy/improving block chance if so.
    if defender.db.is_bracing:
        accuracy -= 10
    # Checking to see if the defender is_rushing and improving accuracy if so.
    if defender.db.is_rushing:
        accuracy += 5
    # Checking to see if the defender used_ranged and improving accuracy if so.
    if defender.db.used_ranged:
        accuracy += 5
    # Checking to see if the defender is Petrified and reducing accuracy if so.
    if defender.db.debuffs["Petrify"][0] > 0:
        accuracy -= 12
    if accuracy > 99:
        accuracy = 99
    elif accuracy < 1:
        accuracy = 1
    return accuracy


def interrupt_chance_calc(interrupter, incoming_attack_instance, outgoing_interrupt):
    interrupt_chance = 40 + int(outgoing_interrupt.acc) - int(incoming_attack_instance.attack.acc)
    if interrupter.db.is_baiting:
        interrupt_chance += 10
    if interrupter.db.is_rushing:
        interrupt_chance -= 5
    if interrupter.db.used_ranged:
        interrupt_chance -= 5
    if incoming_attack_instance.has_priority:
        interrupt_chance -= 15
    if "Priority" in outgoing_interrupt.effects:
        interrupt_chance += 15
    if incoming_attack_instance.has_ranged:
        if "Long-Range" not in outgoing_interrupt.effects:
            interrupt_chance -= 15
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
    ex_gain = int(damage_inflicted) / 15
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


def apply_attack_effects_to_attacker(attacker, attack):
    # This function checks for effects on an attack and modifies the attacker's status accordingly.
    # Modify this function as more effects are implemented.
    # First, reset any effects from the previous round.
    attacker.db.is_rushing = False
    attacker.db.is_weaving = False
    attacker.db.is_bracing = False
    attacker.db.is_baiting = False
    attacker.db.used_ranged = False
    # Now, apply the new attack effects.
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
            if effect == "Long-Range":
                attacker.db.used_ranged = True
    return attacker


def accrue_block_penalty(defender, pre_block_damage, block_bool, attack_instance):
    # If the block succeeds, accrue full block penalty. If the block fails, accrue a minor block penalty.
    # Crush makes the block penalty a lot worse if you block and a little worse if you fail to block.
    if block_bool:
        if attack_instance.has_crush:
            defender.db.block_penalty += (pre_block_damage / 5)
        else:
            defender.db.block_penalty += (pre_block_damage / 10)
    else:
        if attack_instance.has_crush:
            defender.db.block_penalty += (pre_block_damage / 15)
        else:
            defender.db.block_penalty += (pre_block_damage / 30)
    return defender.db.block_penalty


def final_action_check(character):
    # After any reaction in which the character takes damage, check if their LF has dropped to 0 or below.
    if character.db.lf <= 0 and not character.db.final_action:
        # No longer setting LF to 0 at this juncture, so that Regen can't necessarily revive you.
        character.db.final_action = True
        character.msg("You have been reduced below 0 LF. Your next action will be your last. Any attacks will"
                      " suffer a penalty to your accuracy.")


def final_action_taken(character):
    # Call with conditional: if character.db.final_action ...
    # Confirm that the target has not been healed out of their final_action
    if character.db.lf > 0:
        if character.db.revived_during_final_action:
            character.db.final_action = False
            return character.msg("As you have been revived, you may continue to fight.")
        else:
            character.db.final_action = False
            character.db.stunned = True
            return character.msg("You are stunned for one turn. On your next turn, you must 'pass' unless revived.")
    if not character.db.negative_lf_from_dot:
        character.db.final_action = False
        character.db.KOed = True
        character.db.lf = 0
        # Now LF is set to 0, so it's easier to revive someone and there's no benefit to beating on anyone excessively.
        character.msg("You have taken your final action and can no longer fight.")
        combat_string = "|y<COMBAT>|n {0} can no longer fight.".format(character.name)
        character.location.msg_contents(combat_string)
        combat_log_entry(character, combat_string)


def combat_log_entry(caller, logstring):
    # This function is called when adding "<COMBAT>" messages to the autologger, so that people reading logs of combat
    # scenes can contextualize the RP with the blow-by-blow record of fights.
    if caller.location.db.active_event:
        scene = Scene.objects.get(pk=caller.location.db.event_id)
        scene.addLogEntry(LogEntry.EntryType.COMBAT, escape(logstring), caller)


def find_attacker_stat(attacker, base_stat):
    # Use the base stat of the attack to pull the attacker's corresponding stat value.
    attacker_stat = 0
    if base_stat == "Power":
        attacker_stat += attacker.db.power
    if base_stat == "Knowledge":
        attacker_stat += attacker.db.knowledge
    return attacker_stat


def heal_check(action, healer, target):
    # Check for heal effect. Check has_been_healed: how much the target has already been healed this fight.
    # Come up with a formula for accuracy of heal to affect variance of heal amount (more accurate, more consistent).
    # Come up with a formula to depreciate healing amount based on has_been_healed, and apply that after variance.
    # Then make custom in-room announcement and end turn, to avoid putting any of this code into CmdAttack.

    # Regen_check passes heal_check the string "regen" rather than an Attack instance, so make a substitute action.
    regen = False
    if action == "regen":
        regen = True
        action = Attack("", 0, 50, 50, "", [])
        base_stat = 20
    # Set baseline healing amount based on Art Damage and healer's stat. This replaces damage_calc.
    else:
        if action.stat.lower() == "power":
            base_stat = healer.db.power
        if action.stat.lower() == "knowledge":
            base_stat = healer.db.knowledge
        # Check for Vigor buff on healer.
        base_stat = vigor_check(healer, base_stat)
    # Weird corner case: see if someone is trying to heal themselves out of KO state.
    if "Heal" in action.effects and healer == target and healer.db.final_action:
        return healer.msg("You may not heal or revive yourself as a final action.")
    if "Drain" in action.effects:
        total_healing = action.dmg / 2.5
    else:
        healing = 1.55 * action.dmg
        healing_multiplier = (0.00583 * healing) + 0.708
        total_healing = (healing + base_stat) * healing_multiplier
    # logger(healer, "Healing after multiplier: " + str(total_healing))
    # Then, apply variance to healing amount based on Art Accuracy.
    # Currently, there's minimal variance above 80 Accuracy, and then more as you go down.
    # TODO: More complex calculation for slope of increase in variance as accuracy decreases.
    accuracy = action.acc
    if action.acc > 80:
        accuracy = 80
    base_variance = math.ceil((80 - accuracy) * 3)
    variance = random.randrange(base_variance*-1, base_variance)
    total_healing += variance
    # logger(healer, "Healing after variance: " + str(total_healing))
    # Finally, check the target's has_been_healed and reduce how much they will be healed accordingly.
    if target.db.has_been_healed > 0:
        # I want healing to depreciate quickly, so the second is "meh" and the third is bad.
        healing_reduction_multiplier = 1 - ((target.db.has_been_healed / target.db.maxlf) * 1.5)
        if healing_reduction_multiplier < 0:
            healing_reduction_multiplier = 0
        total_healing = total_healing * healing_reduction_multiplier
    # Round to integer.
    total_healing = math.floor(total_healing)
    # Check for the Miasma debuff at this point.
    if target.db.debuffs["Miasma"][0] > 0:
        total_healing = math.ceil(total_healing * 0.5)
    # Heal the target. Not over their maximum LF.
    if (target.db.lf + total_healing) > target.db.maxlf:
        # This should get the target to their max LF.
        total_healing = target.db.maxlf - target.db.lf
    target.db.lf += total_healing
    target.db.has_been_healed += total_healing
    # Announce healing to room and end the healer's turn as per CmdAttack.
    if "Heal" in action.effects and healer != target:
        healer.msg("You healed {target} with {action} for {value}.".format(target=target, action=action,
                                                                           value=total_healing))
        target.msg("You have been healed by {healer} with {action} for {value}.". format(healer=healer, action=action,
                                                                                         value=total_healing))
        combat_string = "|y<COMBAT>|n {attacker} has healed {target} with {action}.".format(
            attacker=healer.key, target=target, action=action)
        healer.location.msg_contents(combat_string)
    elif "Heal" in action.effects and healer == target:
        healer.msg("You healed yourself with {action} for {value}.".format(action=action,
                                                                           value=total_healing))
        combat_string = "|y<COMBAT>|n {attacker} has healed themselves with {action}.".format(
            attacker=healer.key, action=action)
        healer.location.msg_contents(combat_string)
    if regen:
        healer.msg("You have regenerated for {value}.".format(value=total_healing))
    # Incorporate Support effects
    else:
        apply_buff(action, healer, target)

    # Incorporate revival, i.e., being healed up from 0 LF and out of KO state
    # Corner casing: if someone else has already done a normal heal, leaving the target stunned, a raise will fix that
    if "Revive" in action.effects and target.db.stunned:
        target.db.stunned = False
        target.msg("You are revived and thus no longer stunned.")
    if target.db.KOed:
        target.db.KOed = False
        if "Revive" in action.effects:
            target.msg("You are revived: you may rejoin the fight and act as normal on your next turn.")
        else:
            target.db.stunned = True
            target.msg("You are healed but stunned: you may rejoin the fight after using 'pass' on your next turn.")
    # Someone could be healed during their final action but before being KOed. Let's have raise help there too
    if target.db.final_action and target.db.lf > 0:
        if regen:
            target.msg("You have regenerated sufficiently to continue fighting!")
            target.db.final_action = False
        elif "Revive" in action.effects:
            target.db.revived_during_final_action = True
            target.msg("Your next action will still have a final action penalty, but you will not be KOed.")
        else:
            target.msg("Your next action still has a final action penalty. After taking it, you will be stunned "
                       "for one turn but not KOed.")


def drain_check(action, attacker, target, damage_dealt):
    # Weird corner case: you cannot Drain from yourself.
    if attacker != target:
    # For the purposes of self-healing, treat the power of the attack as relative to the damage it dealt (so less if blocked)
        action.dmg = damage_dealt
        heal_check(action, attacker, attacker)
    # But don't "return" here, because the rest of the attack will proceed as normal after self-healing


def regen_check(character):
    # Route the Regen effect through heal_check so that all healing works the same. Use a string, "regen."
    heal_check("regen", character, character)
    character.db.buffs["Regen"] -= 1
    if character.db.buffs["Regen"] == 0:
        character.msg("You are no longer gradually regenerating.")


def vigor_check(character, base_stat):
    # Checks if the character has the Vigor buff, and if so, Power/Knowledge is effectively +25.
    if character.db.buffs["Vigor"] > 0:
        base_stat += 25
    return base_stat


def dispel_check(target):
    # If an Art with Dispel successfully hits or is endured, check for buffs on the target and remove one at random.
    dispel_targets = []
    for status_effect, duration in target.db.buffs.items():
        if target.db.buffs[status_effect] > 0:
            dispel_targets.append(status_effect)
    # Dispel_targets should now be a list of the names of all active buffs on the target.
    if dispel_targets:
        dispel_target = random.choice(dispel_targets)
        modified_buffs = target.db.buffs
        modified_buffs[dispel_target] = 0
        target.msg(dispel_target.title() + " has been dispelled.")
        # Return the target's updated status effects if one has been dispelled.
        return modified_buffs


def critical_hits(damage, attacker):
    # Default 5% chance to inflict 1.25x damage. There will be ways to modify that, so put them all here.
    # Take the current damage as an input and return a bool and possibly modified damage.
    is_critical = False
    critical_check = random.randint(1, 100)
    critical_threshold = 5
    # Checking for Acuity buff on the attacker.
    if attacker.db.buffs["Acuity"] > 0:
        critical_threshold *= 3
    if critical_check <= critical_threshold:
        is_critical = True
        damage *= 1.25
    return is_critical, damage


def protect_and_reflect_check(incoming_damage, defender, attack, interrupt_success):
    # Protect and Reflect mitigate damage specifically for an interrupter when interrupting.
    if (defender.db.buffs["Protect"] > 0 and attack.stat.lower() == "power") or (defender.db.buffs["Reflect"] > 0 and attack.stat.lower() == "knowledge"):
        if interrupt_success:
            incoming_damage = incoming_damage * 0.75
        else:
            incoming_damage = incoming_damage * 0.85
    return incoming_damage


def modify_aim_and_feint(accuracy, reaction, aim_or_feint):
    # Centralizing any modifications to Aim and Feint from buffs, etc. Call this in each reaction. Return mod acc.
    if reaction == "dodge" or "block":
        # Aiming is more accurate and feinting is less accurate against dodging and blocking.
        if aim_or_feint == AimOrFeint.AIM:
            accuracy += 15
        elif aim_or_feint == AimOrFeint.HASTED_AIM:
            accuracy += 25
        elif aim_or_feint == AimOrFeint.FEINT:
            accuracy -= 15
    elif reaction == "endure" or "interrupt":
        # Aiming is less accurate and feinting is more accurate against enduring and interrupting.
        if aim_or_feint == AimOrFeint.AIM:
            accuracy -= 15
        elif aim_or_feint == AimOrFeint.FEINT:
            accuracy += 15
        elif aim_or_feint == AimOrFeint.BLINKED_FEINT:
            accuracy += 25
    if accuracy > 99:
        accuracy = 99
    elif accuracy < 1:
        accuracy = 1
    return accuracy


def poison_check(target):
    # LF is an integer and final_action is a bool. When LF is reduced to 0, final_action is set to True. When someone
    # takes their turn and final_action is True, only then are they KOed. It is possible to be healed out of
    # final_action, including by the Regen buff (see heal_check). In this context, how should Poison work?
    #
    # I think I want the logic to be that Regen can *save* you from being KOed if it's your final action, but Poison
    # cannot kill you *unless* it is already your final action and you are not healed out of it. So I want to prevent:
    # 1) Not final action -> takes action -> Poison damage reduces LF below 0 -> insta-KOed (bullshit)
    # 2) Not final action -> takes action -> Poison damage reduces LF below 0 -> final_action isn't set to True (oops!)
    #
    # Since combat_tick is called before final_action_taken, that works fine for regen, but if poison can potentially
    # apply final_action, I need to create a special case for, after regen, checking if poison knocks you under 0 LF
    # to apply final_action without triggering final_action_taken. (As in, if poison specifically reduces you below 0
    # LF after taking your turn, you are not insta-KOed, but still get another turn as a final action.)
    #
    # I'll try creating this special case here and passing it to final_action_taken, rather than having poison_check()
    # itself apply final_action.
    poison_damage = random.randint(20, 60)
    # MotM's "Deadly" effect is a tradeoff that reduces damage upfront but deals more over time. Currently, Poison is
    # just more damage, which may be OP, but it can also be Cured, so... I'll use the typical RPG paradigm for now.
    target.db.lf -= poison_damage
    target.msg("You have taken {damage} damage from poison.".format(damage=poison_damage))
    initial_state = target.db.final_action
    final_action_check(target)
    # Check if it's now your final_action BECAUSE of the poison damage specifically.
    if target.db.final_action and not initial_state:
        target.db.negative_lf_from_dot = True
    # This check will only be called if Poison's duration is already greater than 1.
    target.db.debuffs["Poison"][0] -= 1
    if target.db.debuffs["Poison"][0] == 0:
        target.msg("You are no longer poisoned.")


def ranged_knockback(defender, attacker):
    # Called when a target is struck by a Long-Range attack and suffers knockback against the attacker.
    defender.db.ranged_knockback[0] = True
    defender.db.ranged_knockback[1].append(attacker.key)
    defender.msg("You have been knocked back from {attacker} by a ranged attack.".format(attacker=attacker.key))


def wound_check(character, action):
    # Check the AP cost of the action and, if any, inflict damage to a wounded character.
    if action and action.ap < 0:
        damage_floor = action.ap * -1
        damage_ceil = math.ceil(damage_floor * 2.5)
        wound_damage = random.randint(damage_floor, damage_ceil)
        character.db.lf -= wound_damage
        character.msg("You have taken {damage} damage from your wound.".format(damage=wound_damage))
        initial_state = character.db.final_action
        final_action_check(character)
        # Check if it's now your final_action BECAUSE of the poison damage specifically.
        if character.db.final_action and not initial_state:
            character.db.negative_lf_from_dot = True
        # This check will only be called if Wound's duration is already greater than 1.
    character.db.debuffs["Wound"][0] -= 1
    if character.db.debuffs["Wound"][0] == 0:
        character.msg("You are no longer wounded.")


def berserk_check(caller, attack):
    # If an attacker is Berserk, check if the attack is above 50 Force/Damage and, if not, prevent them from attacking.
    if attack.dmg < 50:
        return True
    # Simple for now, but if this seems OP, I may change it so weaker attacks cost more AP or some EX from caller.


# FUNCTIONS TO BE MODIFIED WHEN NEW EFFECTS ARE IMPLEMENTED IN EFFECTS.PY
# Combat_tick for reducing duration; normalize_status for CmdRestore; display_status_effects for CmdCheck strings;
# and apply_buff or apply_debuff for buffs and debuffs respectively.


def combat_tick(character, action):
    # This function represents a "tick" or the end of a turn. Any "action," like +attack or +pass, counts as a tick.
    character.db.endure_bonus = 0
    character.db.is_aiming = False
    character.db.is_feinting = False
    character.db.ranged_knockback = [False, []]
    character.db.negative_lf_from_dot = False
    # Currently, reduce block penalty per tick by 7 or a third, whichever is higher.
    if character.db.block_penalty > 0:
        if (character.db.block_penalty / 3) > 7:
            block_penalty_reduction = character.db.block_penalty / 3
        else:
            block_penalty_reduction = 7
        if block_penalty_reduction - 7 < 0:
            character.db.block_penalty = 0
        else:
            character.db.block_penalty -= block_penalty_reduction
    # Check for Regen
    for status_effect, duration in character.db.buffs.items():
        if status_effect == "Regen" and duration > 0:
            regen_check(character)
        else:
            if character.db.buffs[status_effect] > 0:
                character.db.buffs[status_effect] -= 1
                if character.db.buffs[status_effect] == 0:
                    if status_effect == "Vigor":
                        character.msg("You are no longer invigorated.")
                    elif status_effect == "Protect":
                        character.msg("You are no longer protected from attacks.")
                    elif status_effect == "Reflect":
                        character.msg("You are no longer reflecting attacks.")
                    elif status_effect == "Acuity":
                        character.msg("You are no longer acutely attentive to critical vulnerabilities.")
                    elif status_effect == "Haste":
                        character.msg("You are no longer hastened.")
                    elif status_effect == "Blink":
                        character.msg("You are no longer trailed by afterimages.")
                    elif status_effect == "Bless":
                        character.msg("Your resistance to debilitating effects is no longer enhanced.")
    for status_effect, duration_and_resist in character.db.debuffs.items():
        duration = duration_and_resist[0]
        if status_effect == "Poison" and duration > 0:
            poison_check(character)
        elif status_effect == "Wound" and duration > 0:
            wound_check(character, action)
        elif duration > 0:
            duration_and_resist[0] -= 1
            if duration_and_resist[0] == 0:
                if status_effect == "Curse":
                    character.msg("You are no longer cursed.")
                elif status_effect == "Injure":
                    character.msg("You are no longer injured.")
                elif status_effect == "Muddle":
                    character.msg("You are no longer muddled.")
                elif status_effect == "Miasma":
                    character.msg("You are no longer afflicted by a miasma.")
                elif status_effect == "Berserk":
                    character.msg("You are no longer berserk.")
                elif status_effect == "Petrify":
                    character.msg("You are no longer petrified.")


def normalize_status(character):
    # This function sets every status effect to default/neutral state.
    character.db.is_aiming = False
    character.db.is_feinting = False
    character.db.is_rushing = False
    character.db.is_weaving = False
    character.db.is_bracing = False
    character.db.is_baiting = False
    character.db.used_ranged = False
    character.db.ranged_knockback = [False, []]
    character.db.buffs = {"Regen": 0, "Vigor": 0, "Protect": 0, "Reflect": 0, "Acuity": 0, "Haste": 0, "Blink": 0,
                          "Bless": 0}
    character.db.debuffs = {"Poison": [0, 0], "Wound": [0, 0], "Curse": [0, 0], "Injure": [0, 0], "Muddle": [0, 0],
                            "Miasma": [0, 0], "Berserk": [0, 0], "Petrify": [0, 0]}
    character.db.negative_lf_from_dot = False
    character.db.block_penalty = 0
    character.db.final_action = False
    character.db.KOed = False
    character.db.stunned = False
    character.db.revived_during_final_action = False
    character.db.endure_bonus = 0
    character.db.has_been_healed = 0


def display_status_effects(caller):
    # Called by the check command to display status effects.
    if caller.db.block_penalty > 0:
        caller.msg("Your current block penalty is {0}%.".format(round(caller.db.block_penalty)))
    if caller.db.endure_bonus > 0:
        caller.msg("Your current endure bonus to accuracy is {0}%.".format(caller.db.endure_bonus))
    if caller.db.final_action:
        caller.msg("You have been reduced below 0 LF. Your next action will be your last and your accuracy is lowered.")
    if caller.db.is_weaving:
        caller.msg("You are currently weaving, increasing your chance to dodge until your next action.")
    if caller.db.is_bracing:
        caller.msg("You are currently bracing, increasing your chance to block until your next action.")
    if caller.db.is_baiting:
        caller.msg("You are currently baiting, increasing your chance to interrupt until your next action.")
    if caller.db.is_rushing:
        caller.msg("You are currently rushing, decreasing your reaction chances until your next action.")
    if caller.db.used_ranged:
        caller.msg("You previously attacked at long range, decreasing your reaction chances until your next action.")
    if caller.db.ranged_knockback[0] and len(caller.db.ranged_knockback[1]) == 1:
        caller.msg("You are suffering a knockback penalty of reduced accuracy against {attacker}.".format(
            attacker=caller.db.ranged_knockback[1][0]))
    elif caller.db.ranged_knockback[0] and len(caller.db.ranged_knockback[1]) > 1:
        formatted_attackers_string = ""
        for attacker in caller.db.ranged_knockback[1]:
            if caller.db.ranged_knockback[1].index(attacker) == len(caller.db.ranged_knockback[1]) - 1:
                formatted_attackers_string += (attacker + ".")
            else:
                formatted_attackers_string += (attacker + ", ")
        caller.msg("You are suffering knockback penalties of reduced accuracy against: {attackers}".format(
            attackers=formatted_attackers_string))
    for status_effect, duration in caller.db.buffs.items():
        if caller.db.buffs[status_effect] > 0:
            if status_effect == "Regen":
                if duration > 1:
                    caller.msg("You will gradually regenerate for {duration} rounds.".format(duration=duration))
                else:
                    caller.msg("You will gradually regenerate for 1 more round.")
            elif status_effect == "Vigor":
                if duration > 1:
                    caller.msg("You are invigorated for {duration} rounds.".format(duration=duration))
                else:
                    caller.msg("You are invigorated for 1 more round.")
            elif status_effect == "Protect":
                if duration > 1:
                    caller.msg("You are protected for {duration} rounds.".format(duration=duration))
                else:
                    caller.msg("You are protected for 1 more round.")
            elif status_effect == "Reflect":
                if duration > 1:
                    caller.msg("You are reflective for {duration} rounds.".format(duration=duration))
                else:
                    caller.msg("You are reflective for 1 more round.")
            elif status_effect == "Acuity":
                if duration > 1:
                    caller.msg("You are acutely attentive to critical vulnerabilities for {duration} rounds.".format(
                        duration=duration))
                else:
                    caller.msg("You are acutely attentive to critical vulnerabilities for 1 more round.")
            elif status_effect == "Haste":
                if duration > 1:
                    caller.msg("You are hastened for {duration} rounds.".format(duration=duration))
                else:
                    caller.msg("You are hastened for 1 more round.")
            elif status_effect == "Blink":
                if duration > 1:
                    caller.msg("You are trailed by afterimages for {duration} rounds.".format(duration=duration))
                else:
                    caller.msg("You are trailed by afterimages for 1 more round.")
            elif status_effect == "Bless":
                if duration > 1:
                    caller.msg("Your resistance to debilitating effects is enhanced for {duration} rounds.".format(
                        duration=duration))
    for status_effect, duration_and_resist in caller.db.debuffs.items():
        duration = duration_and_resist[0]
        if status_effect == "Poison" and duration > 0:
            if duration > 1:
                caller.msg("You are poisoned and suffering damage over time for {duration} rounds.".format(
                    duration=duration))
            else:
                caller.msg("You are poisoned and suffering damage over time for 1 more round.")
        elif status_effect == "Wound" and duration > 0:
            if duration > 1:
                caller.msg("You are wounded and suffering damage when you exert yourself for {duration} rounds.".format(
                    duration=duration))
            else:
                caller.msg("You are wounded and suffering damage when you exert yourself for 1 more round.")
        elif status_effect == "Curse" and duration > 0:
            if duration > 1:
                caller.msg("You are cursed, increasing your vulnerability to debilitating effects for {duration} "
                           "rounds.".format(duration=duration))
            else:
                caller.msg("You are cursed, increasing your vulnerability to debilitating effects for 1 more round.")
        elif status_effect == "Injure" and duration > 0:
            if duration > 1:
                caller.msg("You are injured, reducing your effective Power, Parry, and Speed for {duration} rounds.".
                           format(duration=duration))
            else:
                caller.msg("You are injured, reducing your effective Power, Parry, and Speed for 1 more round.")
        elif status_effect == "Muddle" and duration > 0:
            if duration > 1:
                caller.msg("You are muddled, reducing your effective Knowledge, Barrier, and Speed for {duration} rounds.".
                           format(duration=duration))
            else:
                caller.msg("You are muddled, reducing your effective Knowledge, Barrier, and Speed for 1 more round.")
        elif status_effect == "Miasma" and duration > 0:
            if duration > 1:
                caller.msg("You are afflicted by a miasma that halves the effects of healing upon you for {duration} rounds.".
                           format(duration=duration))
            else:
                caller.msg("You are afflicted by a miasma that halves the effects of healing upon you for 1 more round.")
        elif status_effect == "Berserk" and duration > 0:
            if duration > 1:
                caller.msg("You are berserk, increasing your effective Power, Knowledge, and Speed but preventing you "
                           "from using Arts with a Force of less than 50 for {duration} rounds.".format(duration=duration))
            else:
                caller.msg("You are berserk, increasing your effective Power, Knowledge, and Speed but preventing you "
                           "from using Arts with a Force of less than 50 for 1 more round.")
        elif status_effect == "Petrify" and duration > 0:
            if duration > 1:
                caller.msg("You are petrified, reducing your Speed and especially your Dodge chances but somewhat"
                           "increasing your Block and Endure chances for {duration} rounds.".format(duration=duration))
            else:
                caller.msg("You are petrified, reducing your Speed and especially your Dodge chances but somewhat"
                           "increasing your Block and Endure chances for 1 more round.")


def apply_buff(action, healer, target):
    # A sub-function for heal_check so that the logic of buff application need not repeat.
    application_string = ""
    extension_string = ""
    buff_effects = []
    serendipity = False
    # Find all the effects on the action that are buffs.
    split_effect_list = action.effects.split()
    for effect in split_effect_list:
        if effect == "Serendipity":
            serendipity = True
        for buff in BUFFS:
            if effect == buff.name:
                buff_effects.append(effect)
    if serendipity:
        # Add an additional random buff that is not already one of the Art's effects.
        buff_options = []
        for buff in BUFFS:
            if buff.name not in buff_effects:
                buff_options.append(buff.name)
        buff_effects.append(random.choice(buff_options))
    for buff in buff_effects:
        if buff == "Regen":
            application_string = "You will gradually regenerate health."
            extension_string = "The duration of your gradual regeneration has been extended."
        elif buff == "Vigor":
            application_string = "You are invigorated, increasing your effective Power and Knowledge."
            extension_string = "The duration of your invigoration has been extended."
        elif buff == "Protect":
            application_string = "You are protected, increasing your Parry and damage mitigation when interrupting " \
                                 "Power-type attacks."
            extension_string = "The duration of your protection has been extended."
        elif buff == "Reflect":
            application_string = "You are reflective, increasing your Barrier and damage mitigation when interrupting " \
                                 "Knowledge-type attacks."
            extension_string = "The duration of your reflectiveness has been extended."
        elif buff == "Acuity":
            application_string = "You are acutely attentive to critical vulnerabilities, increasing your Speed and " \
                                 "your chance of inflicting a critical hit."
            extension_string = "The duration of your acute attention to critical vulnerabilities has been extended."
        elif buff == "Haste":
            application_string = "You are hastened, increasing your Speed and the effectiveness of Aim."
            extension_string = "The duration of your hastened state has been extended."
        elif buff == "Blink":
            application_string = "You are trailed by afterimages, increasing your Speed and the effectiveness of Feint."
            extension_string = "The duration of your afterimages has been extended."
        elif buff == "Bless":
            application_string = "Your resistance to debilitating effects has been enhanced."
            extension_string = "The duration of your enhanced resistance to debilitating effects has been extended."
        # Now apply the buff using consistent logic
        if target.db.buffs[buff] == 0:
            target.msg(application_string)
        else:
            target.msg(extension_string)
        if healer == target:
            # A combat tick is going to happen after this, so the duration will be 3 regardless.
            target.db.buffs[buff] = 4
        else:
            target.db.buffs[buff] = 3


def apply_debuff(action, debuffer, target):
    # Debuffs have a chance to be resisted. This can be increased by buffs, and some debuffs increase the afflicted's
    # resistance to being afflicted again in the same fight (to disincentivize spamming them).
    base_debuff_resist = 30
    if target.db.buffs["Bless"] > 0:
        base_debuff_resist += 20
    if target.db.debuffs["Curse"][0] > 0:
        base_debuff_resist -= 20
    application_string = ""
    extension_string = ""
    debuff_effects = []
    # Find all the effects on the action that are debuffs.
    split_effect_list = action.effects.split()
    for effect in split_effect_list:
        for debuff in DEBUFFS:
            if effect == debuff.name:
                debuff_effects.append(effect)
    # if serendipity:
        # Add an additional random buff that is not already one of the Art's effects.
        # buff_options = []
        # for buff in BUFFS:
            # if buff.name not in buff_effects:
                # buff_options.append(buff.name)
        # buff_effects.append(random.choice(buff_options))
    for debuff in debuff_effects:
        # Identify the debuff and calculate the specific resistance (overwrite debuff_resist each time)
        debuff_resist = base_debuff_resist + target.db.debuffs[debuff][1]
        if debuff == "Poison":
            application_string = "You are poisoned, gradually losing health."
            extension_string = "The duration of your poisoning has been extended."
        elif debuff == "Wound":
            application_string = "You are wounded and will suffer damage when you exert yourself."
            extension_string = "The duration of your wounds has been extended."
        elif debuff == "Curse":
            application_string = "You are cursed, increasing your vulnerability to debilitating effects."
            extension_string = "The duration of your curse has been extended."
        elif debuff == "Injure":
            application_string = "You are injured, reducing your effective Power, Parry, and Speed."
            extension_string = "The duration of your injury has been extended."
        elif debuff == "Muddle":
            application_string = "You are muddled, reducing your effective Knowledge, Barrier, and Speed."
            extension_string = "The duration of your muddled state has been extended."
        elif debuff == "Miasma":
            application_string = "You are afflicted by a miasma, halving the effectiveness of healing upon you."
            extension_string = "The duration of the miasma afflicting you has been extended."
        elif debuff == "Berserk":
            application_string = "You have gone berserk, increasing your effective Power, Knowledge, and Speed but " \
                                 "compelling you to use more damaging, less accurate attacks."
            extension_string = "The duration of your berserk fury has been extended."
        elif debuff == "Petrify":
            application_string = "You are petrified, reducing your Speed and especially your Dodge chances but " \
                                 "somewhat increasing your Block and Endure chances."
            extension_string = "The duration of your petrifaction has been extended."
        # Roll the debuff check
        debuff_check_roll = random.randint(1, 100)
        if debuff_check_roll > debuff_resist:
            # If debuff succeeds, apply using consistent logic
            if target.db.debuffs[debuff][0] == 0:
                target.msg(application_string)
            else:
                target.msg(extension_string)
            if debuffer == target:
                # A combat tick is going to happen after this, so the duration will be 3 regardless. If it matters...?
                target.db.debuffs[debuff][0] = 4
            else:
                target.db.debuffs[debuff][0] = 3
