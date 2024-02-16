from world.scenes.models import Scene, LogEntry
from django.utils.html import escape
from evennia.objects.models import ObjectDB
import random
import math
from world.utilities.utilities import logger
from world.combat.attacks import Attack


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


def damage_calc(attack_dmg, attacker_stat, base_stat, parry, barrier):
    def_stat = 0
    if base_stat == "Power":
        def_stat = parry
    if base_stat == "Knowledge":
        def_stat = barrier
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
    return accuracy


def modify_damage(action, character):
    damage = action.dmg
    # Modify attack damage based on base stat.
    if action.stat.lower() == "power":
        base_stat = character.db.power
    if action.stat.lower() == "knowledge":
        base_stat = character.db.knowledge
    damage_multiplier = (0.00583 * damage) + 0.708
    total_damage = (damage + base_stat) * damage_multiplier
    return total_damage


def modify_speed(speed):
    # A function to nest within the reaction functions to soften the effects of low and high Speed.
    speed_multiplier = speed * -0.00221 + 1.25
    effective_speed = speed * speed_multiplier
    return effective_speed


def dodge_calc(defender, attack_instance):
    # accuracy = int(int(attack_acc) / (speed/100))
    speed = defender.db.speed
    attack_acc = attack_instance.attack.acc
    accuracy = 100.0 - (0.475 * (modify_speed(speed) - attack_acc) + 5)
    # Checking to see if the attack has sweep and improving accuracy/reducing dodge chance if so.
    if attack_instance.has_sweep:
        accuracy += 10
    # Checking to see if the defender is_rushing and improving accuracy if so.
    if defender.db.is_rushing:
        accuracy += 5
    # Checking to see if the defender is_weaving and reducing accuracy/improving dodge chance if so.
    if defender.db.is_weaving:
        accuracy -= 10
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
    averaged_def = modify_speed(speed) + def_stat*.5
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
    averaged_def = modify_speed(speed) + def_stat*.5
    # accuracy = int(int(attack_acc) / (averaged_def / 100))
    accuracy = 100.0 - (0.475 * (averaged_def - attack_acc))
    # Checking to see if the defender is_bracing and reducing accuracy/improving block chance if so.
    if defender.db.is_bracing:
        accuracy -= 10
    # Checking to see if the defender is_rushing and improving accuracy if so.
    if defender.db.is_rushing:
        accuracy += 5
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
    if incoming_attack_instance.has_priority:
        interrupt_chance -= 15
    if "Priority" in outgoing_interrupt.effects:
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


def normalize_status(character):
    # This function sets every status effect to default/neutral state.
    character.db.is_aiming = False
    character.db.is_feinting = False
    character.db.is_rushing = False
    character.db.is_weaving = False
    character.db.is_bracing = False
    character.db.is_baiting = False
    character.db.regen_duration = 0
    character.db.block_penalty = 0
    character.db.final_action = False
    character.db.KOed = False
    character.db.stunned = False
    character.db.revived_during_final_action = False
    character.db.endure_bonus = 0
    character.db.has_been_healed = 0


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


def combat_tick(character):
    # This function represents a "tick" or the end of a turn. Any "action," like +attack or +pass, counts as a tick.
    character.db.endure_bonus = 0
    character.db.is_aiming = False
    character.db.is_feinting = False
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
    if character.db.regen_duration > 0:
        regen_check(character)
    return character


def apply_attack_effects_to_attacker(attacker, attack):
    # This function checks for effects on an attack and modifies the attacker's status accordingly.
    # Modify this function as more effects are implemented.
    # First, reset any effects from the previous round.
    attacker.db.is_rushing = False
    attacker.db.is_weaving = False
    attacker.db.is_bracing = False
    attacker.db.is_baiting = False
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
    if character.db.lf <= 0:
        # Whenever LF drops below 0, set it at 0. This is to facilitate raising in party combat.
        character.db.lf = 0
        character.db.final_action = True
        character.msg("You have been reduced to 0 LF. Your next action will be your last. Any attacks will"
                      " suffer a penalty to your accuracy.")
    return character


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
    character.db.final_action = False
    character.db.KOed = True
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
    if caller.db.regen_duration > 0:
        if caller.db.regen_duration > 1:
            caller.msg(f"You will gradually regenerate for {caller.db.regen_duration} rounds.")
        else:
            caller.msg("You will gradually regenerate for 1 more round.")


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
    # logger(healer, "Healing after depreciation: " + str(total_healing))
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
    if "Regen" in action.effects:
        if target.db.regen_duration == 0:
            target.db.regen_duration = 3
            target.msg("You will gradually regenerate health for 3 rounds.")
        else:
            target.db.regen_duration = 3
            target.msg("The duration of your gradual regeneration has been extended to 3 rounds.")

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
    if target.db.final_action:
        if regen:
            target.msg("You have regenerated sufficiently to continue fighting!")
            target.db.final_action = False
        elif "Revive" in action.effects:
            target.db.revived_during_final_action = True
            target.msg("Your next action will still have a final action penalty, but you will not be KOed.")
        else:
            target.msg("Your next action still has a final action penalty. After taking it, you will be stunned "
                       "for one turn but not KOed.")
    # If this was the attacker's final action, they are now KOed.
    if healer.db.final_action:
        final_action_taken(healer)


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
    character.db.regen_duration -= 1
    if character.db.regen_duration == 0:
        character.msg("You are no longer gradually regenerating.")