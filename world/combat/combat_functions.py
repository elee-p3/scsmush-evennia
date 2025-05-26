import copy

from world.scenes.models import Scene, LogEntry
from django.utils.html import escape
import random
import math
from world.utilities.utilities import logger
from world.combat.attacks import Attack, ActionResult, AttackToQueue
from world.combat.effects import BUFFS, DEBUFFS, DEBUFFS_STANDARD, DEBUFFS_HEXES, DEBUFFS_TRANSFORMATION, AimOrFeint
from world.combat.normals import NORMALS
from world.arts.models import Arts
from world.utilities.utilities import find_attacker_from_key


class ArtBaseline:
    # A data container to keep a copy of an art prior to it being modified by, e.g., a character's status effects.
    # The purpose is for comparison with base values, e.g., did AP cost go up or down overall.
    def __init__(self, name, base_dmg, base_acc, base_stat, base_ap, base_effects):
        self.name = name
        self.dmg = base_dmg
        self.acc = base_acc
        self.stat = base_stat
        self.ap = base_ap
        self.effects = base_effects


def filter_and_modify_arts(caller):
    # Centralizes the function of sorting through the Arts table, finding those linked to a character, and then
    # modifying them based on the character's status effect. This way, e.g., if a Berserk character's AP costs for
    # attacks of damage less than 50 are increased by 10, this is reflected in both CmdAttack and CmdSheet.
    # This function will be used in CmdAttack, CmdInterrupt, CmdArts, CmdListAttacks, CmdCheck, and CmdSheet.
    arts = Arts.objects.filter(characters=caller)
    base_arts = []
    modified_arts = []
    modified_normals = []
    for art in arts:
        # Copy.copy is used to ensure we do not modify the attack in the character's list, just this instance of it.
        modified_art = copy.copy(art)
        base_art = ArtBaseline(art.name, art.dmg, art.acc, art.stat, art.ap, art.effects)
        base_arts.append(base_art)
        # Modify the copy of the art
        modified_art = berserk_check(caller, modified_art)
        modified_arts.append(modified_art)
    # Now search through the generic normals list and apply the same checks. No need to create a baseline
    for normal in NORMALS:
        modified_normal = copy.copy(normal)
        modified_normal = berserk_check(caller, modified_normal)
        modified_normals.append(modified_normal)
    return modified_arts, base_arts, modified_normals


def assign_attack_instance_id(target):
    # Checks the defender's queue in order to determine the ID number of the new incoming attack instance.
    if not target.db.queue:
        last_id = 0
    else:
        last_id = max((attack.id for attack in target.db.queue))
    new_id = last_id + 1
    return new_id


def damage_calc(queued_attack, defender):
    incoming_attack = queued_attack.attack
    attack_dmg = incoming_attack.dmg
    base_stat = incoming_attack.stat
    attacker = find_attacker_from_key(queued_attack.attacker_key)
    attacker_stat = find_attacker_stat(attacker, base_stat)
    default_dmg = 160

    # Check for the Strain effect on the attack to modify attack_dmg before determining multiplier.
    if queued_attack.has_strain:
        attack_dmg = strain_check(attack_dmg, attacker)

    # base damage will be scaled by the attack's dmg property, with 6 being the baseline 1.0x
    multiplier = 1.0 - ((6 - attack_dmg) * 0.1)

    # stats will affect damage via a flat modifier that depends on a piecewise function
    def_stat = 0
    if base_stat == "Power":
        def_stat = defender.db.parry
    if base_stat == "Knowledge":
        def_stat = defender.db.barrier
    if def_stat == defender.db.parry:
        # Check for Bird or Pig transformations.
        if defender.db.debuffs_transform["Bird"] > 0 or defender.db.debuffs_transform["Pig"] > 0:
            def_stat = math.ceil(def_stat / 2)
        if defender.db.buffs["Protect"] > 0:
            def_stat += 10
        if defender.db.debuffs_standard["Injure"] > 0:
            def_stat -= 10
    if def_stat == defender.db.barrier:
        # Check for Frog or Pumpkin transformations.
        if defender.db.debuffs_transform["Frog"] > 0 or defender.db.debuffs_transform["Pumpkin"] > 0:
            def_stat = math.ceil(def_stat / 2)
        if defender.db.buffs["Reflect"] > 0:
            def_stat += 10
        if defender.db.debuffs_standard["Muddle"] > 0:
            def_stat -= 10

    # Check for Vigor buff (attack.has_vigor).
    attacker_stat = vigor_check(queued_attack, attacker_stat)

    # use modified stat to calculate the flat modifier via a piecewise function
    stat_diff = attacker_stat - def_stat
    abs_stat_diff = abs(stat_diff)
    sign = math.floor(stat_diff/abs_stat_diff)
    if abs_stat_diff <= 25:
        flat_mod = stat_diff
    elif abs_stat_diff <= 50:
        flat_mod = (sign*25) + (sign*(abs_stat_diff-25)*0.7)
    elif abs_stat_diff <= 75:
        # (sign*25) + (sign*25*0.7) + remaining_stat*0.4
        flat_mod = (sign*42.5) + (sign*(abs_stat_diff-50)*0.4)
    else:
        # (sign*25) + (sign*25*0.7) + (sign*25*0.4) + remaining_stat*0.1
        flat_mod = (sign*52.5) + (sign*(abs_stat_diff-75)*0.1)

    final_damage = default_dmg * multiplier + flat_mod

    return final_damage


def attack_switch_check(attacker, switches):
    # Checking for switches on CmdAttack other than heal/cure switches, which go to heal_check.
    # Right now, there is just attack/wild, which lowers accuracy here and increases crit threshold in critical_hits.
    valid_switches = ["wild"]
    error_found = False
    for switch in switches:
        if switch not in valid_switches:
            error_found = True
    return error_found


def modify_speed(speed, defender):
    # Check for relevant buffs and debuffs.
    if defender.db.buffs["Acuity"] > 0:
        speed += 5
    if defender.db.buffs["Haste"] > 0:
        speed += 5
    if defender.db.buffs["Blink"] > 0:
        speed += 5
    if defender.db.debuffs_standard["Injure"] > 0:
        speed -= 5
    if defender.db.debuffs_standard["Muddle"] > 0:
        speed -= 5
    if defender.db.debuffs_standard["Berserk"] > 0:
        speed += 5
    if defender.db.debuffs_standard["Petrify"] > 0:
        speed -= 10
    if defender.db.debuffs_standard["Slime"] > 0:
        speed -= 10
    # All hexes reduce reaction chances a little. Iterate through and count them up.
    hex_count = hex_counter(defender)
    if hex_count > 1:
        if hex_count == 1:
            speed -= 5
        elif hex_count == 2:
            speed -= 9
        elif hex_count == 3:
            speed -= 11
        else:
            speed -= 12
    return speed


# percent chance to hit upon dodge
def dodge_calc(defender, attack_instance: AttackToQueue):
    defender_speed = defender.db.speed
    attack_acc = attack_instance.attack.acc

    # base chance to hit %
    base_chance_to_hit = 45 + attack_acc*5

    # modify base % with speed scaling with respect to a base of 125 via a piecewise function
    speed_diff = 125 - defender_speed
    abs_speed_diff = abs(speed_diff)
    sign = math.floor(speed_diff/abs_speed_diff)

    if abs_speed_diff <= 15:
        mod = 0.7 * speed_diff
    elif abs_speed_diff <= 30:
        # (sign*15*0.7) + remaining_speed_diff*0.4
        mod = (sign*15*0.7) + (sign*(abs_speed_diff-15)*0.4)
    else:
        # (sign*15*0.7) + (sign*15*0.4) + remaining_speed_diff*0.1
        mod = (sign*16.5) + (sign*(abs_speed_diff-30)*0.1)

    chance_to_hit = round(base_chance_to_hit + mod)

    # Checking to see if the attack has sweep and improving accuracy/reducing dodge chance if so.
    if attack_instance.has_sweep:
        chance_to_hit += 10
    # Checking to see if the defender is_rushing and improving accuracy if so.
    if defender.db.is_rushing:
        chance_to_hit += 5
    # Checking to see if the defender is_weaving and reducing accuracy/improving dodge chance if so.
    if defender.db.is_weaving:
        chance_to_hit -= 10
    # Checking to see if the defender used_ranged and improving accuracy if so.
    if defender.db.used_ranged:
        chance_to_hit += 5
    # Checking to see if the defender is Petrified and improving accuracy if so.
    if defender.db.debuffs_standard["Petrify"] > 0:
        chance_to_hit += 12
    # Checking to see if the defender is Slimy and reducing accuracy if so.
    if defender.db.debuffs_standard["Slime"] > 0:
        chance_to_hit -= 12
    if attack_instance.is_final_action:
        chance_to_hit -= 30
    if attack_instance.has_rush:
        chance_to_hit += 7
    if attack_instance.has_ranged:
        chance_to_hit -= 5
    chance_to_hit += attack_instance.endure_bonus
    # cap accuracy at 99%
    if chance_to_hit > 99:
        chance_to_hit = 99
    elif chance_to_hit < 1:
        chance_to_hit = 1
    return chance_to_hit


# percent chance to hit upon block
def block_chance_calc(defender, attack_instance: AttackToQueue):
    def_stat = 0
    if attack_instance.attack.stat == "Power":
        def_stat = defender.db.parry
    if attack_instance.attack.stat == "Knowledge":
        def_stat = defender.db.barrier
    speed = defender.db.speed

    # block stat is an average between the effect-modified speed and the defensive stat
    block_stat = (modify_speed(speed, defender) + def_stat)/2
    base_chance_to_hit = 70

    # modify base % with scaling with respect to a base of 125 via a piecewise function
    stat_diff = 125 - block_stat
    abs_stat_diff = abs(stat_diff)
    sign = math.floor(stat_diff / abs_stat_diff)

    if abs_stat_diff <= 15:
        mod = 0.7 * stat_diff
    elif abs_stat_diff <= 30:
        # (sign*15*0.7) + remaining_speed_diff*0.4
        mod = (sign * 15 * 0.7) + (sign * (abs_stat_diff - 15) * 0.4)
    else:
        # (sign*15*0.7) + (sign*15*0.4) + remaining_speed_diff*0.1
        mod = (sign * 16.5) + (sign * (abs_stat_diff - 30) * 0.1)

    chance_to_hit = round(base_chance_to_hit + mod)

    if attack_instance.has_crush:
        chance_to_hit += 10
    # Checking to see if the defender is_bracing and reducing accuracy/improving block chance if so.
    if defender.db.is_bracing:
        chance_to_hit -= 10
    # Checking to see if the defender is_rushing and improving accuracy if so.
    if defender.db.is_rushing:
        chance_to_hit += 5
    # Checking to see if the defender used_ranged and improving accuracy if so.
    if defender.db.used_ranged:
        chance_to_hit += 5
    # Checking to see if the defender is Petrified and reducing accuracy if so.
    if defender.db.debuffs_standard["Petrify"] > 0:
        chance_to_hit -= 12
    # Checking to see if the defender is Slimy and improving accuracy if so.
    if defender.db.debuffs_standard["Slime"] > 0:
        chance_to_hit += 12
    # Incorporating block penalty.
    chance_to_hit += defender.db.block_penalty
    chance_to_hit += attack_instance.endure_bonus
    # cap block percentage at 99%
    if chance_to_hit > 99:
        chance_to_hit = 99
    elif chance_to_hit < 1:
        chance_to_hit = 1
    return chance_to_hit


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
    if defender.db.debuffs_standard["Petrify"] > 0:
        accuracy -= 12
    # Checking to see if the defender is Slimy and reducing accuracy if so.
    if defender.db.debuffs_standard["Slime"] > 0:
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
    if base_stat == "Power":
        return attacker.db.power
    elif base_stat == "Knowledge":
        return attacker.db.knowledge
    else:
        return 0


def heal_check(action, healer, target, switches):
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
    # See if someone has used a CmdAttack switch to try to Cure a specific debuff that the target does not have.
    cure_match = ""
    # Merging the three debuff dictionaries for this check
    debuffs_all = target.db.debuffs_standard | target.db.debuffs_transform | target.db.debuffs_hexes
    if "Cure" in action.effects and switches:
        # For now, just ensure there's only one switch on attempted Cures.
        if len(switches) > 1:
            return healer.msg("Please specify only one debuff to Cure.")
        for debuff, duration in debuffs_all.items():
            for switch in switches:
                # Switches is a list, so I want to compare with the string within the list.
                if debuff.lower() == switch.lower() and duration == 0:
                    return healer.msg("You have specified a debuff to Cure that the target does not currently have.")
                elif debuff.lower() == switch.lower() and duration > 0:
                    cure_match = debuff
        # After all that, confirm that the switch is an actual existing debuff.
        if not cure_match:
            return healer.msg("You have specified a debuff to Cure that is not recognized.")
    if "Cure" in action.effects and not switches:
        # Select a random active debuff
        debuff_options = []
        for debuff, duration in debuffs_all.items():
            if duration > 0:
                debuff_options.append(debuff)
        if debuff_options:
            cure_match = random.choice(debuff_options)
        # If there are no debuff_options, just let the heal go through as a normal one. No cure_match.
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
    if target.db.debuffs_standard["Miasma"] > 0:
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
    # Actually Cure any debuffs here, after the heal itself.
    if cure_match:
        if cure_match in target.db.debuffs_standard.keys():
            target.db.debuffs_standard[cure_match] = 0
        elif cure_match in target.db.debuffs_transform.keys():
            target.db.debuffs_transform[cure_match] = 0
        elif cure_match in target.db.debuffs_hexes.keys():
            target.db.debuffs_hexes[cure_match] = 0
        status_effect_end_message(target, cure_match)
        healer.msg(f"You have successfully Cured {target}'s {cure_match.title()} status effect.")
    # Incorporate other Support effects
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


def vigor_check(attack, attack_stat):
    # Checks if the character has the Vigor buff, and if so, Power/Knowledge is effectively +25.
    if attack.has_vigor:
        attack_stat += 25
    return attack_stat


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


def critical_hits(damage, action):
    # Default 5% chance to inflict 1.25x damage. There will be ways to modify that, so put them all here.
    # Take the current damage as an input and return a bool and possibly modified damage.
    is_critical = False
    critical_check = random.randint(1, 100)
    critical_threshold = 5
    # Checking for Acuity buff on the attack. (Not the attacker, since their buff might have expired.)
    if action.has_acuity:
        critical_threshold *= 3
    # Attack/wild makes attacks less accurate but adds a flat crit chance bonus, for fun.
    if action.is_wild:
        critical_threshold += 10
    if critical_check <= critical_threshold:
        is_critical = True
        damage *= 1.25
    return is_critical, damage


def damage_message_strings(action_result, caller, attack, damage, interrupt=None, mitigated_damage=None,
                           interrupted_char=None):
    # Consolidated all message strings related to damage here, to reduce repetition in the commands themselves.
    msg_to_room = ""
    # 1: Critically fail to dodge/block/endure
    if action_result == ActionResult.REACT_CRIT_FAIL:
        caller.msg("You have been critically hit by {attack}!".format(attack=attack.name))
        caller.msg("You took {dmg} damage.".format(dmg=round(damage)))
        msg_to_room = "|y<COMBAT>|n {target} has been hit by {attacker}'s {modifier}{attack}.\n" \
                      "|-|r** CRITICAL HIT! **|n"
    # 2: Fail to dodge/block/endure
    elif action_result == ActionResult.REACT_FAIL:
        caller.msg("You have been hit by {attack}.".format(attack=attack.name))
        caller.msg("You took {dmg} damage.".format(dmg=round(damage)))
        msg_to_room = "|y<COMBAT>|n {target} has been hit by {attacker}'s {modifier}{attack}."
    # 3: Glancing blow
    elif action_result == ActionResult.GLANCING_BLOW:
        caller.msg("You have been glanced by {attack}.".format(attack=attack.name))
        caller.msg("You took {dmg} damage.".format(dmg=round(damage)))
        msg_to_room = "|y<COMBAT>|n {target} has been hit by {attacker}'s {modifier}{attack}.\n" \
                      "|-|c** Glancing Blow **|n"
    # 4: Successful dodge (no damage taken)
    elif action_result == ActionResult.DODGE_SUCCESS:
        caller.msg("You have successfully dodged {attack}.".format(attack=attack.name))
        msg_to_room = "|y<COMBAT>|n {target} has dodged {attacker}'s {modifier}{attack}."
    # 5: Successful block (partial damage taken)
    elif action_result == ActionResult.BLOCK_SUCCESS:
        caller.msg("You have successfully blocked {attack}.".format(attack=attack.name))
        caller.msg("You took {dmg} damage.".format(dmg=round(damage)))
        msg_to_room = "|y<COMBAT>|n {target} has blocked {attacker}'s {modifier}{attack}."
    # 6: Successful endure (full damage taken)
    elif action_result == ActionResult.ENDURE_SUCCESS:
        caller.msg("You endure {attack}.".format(attack=attack.name))
        caller.msg("You took {dmg} damage.".format(dmg=round(damage)))
        msg_to_room = "|y<COMBAT>|n {target} endures {attacker}'s {modifier}{attack}."
    # 7: Critically fail to interrupt
    elif action_result == ActionResult.INTERRUPT_CRIT_FAIL:
        caller.msg("You have critically failed to interrupt {attack}!".format(attack=attack.name))
        caller.msg("You took {dmg} damage.".format(dmg=round(damage)))
        msg_to_room = "|y<COMBAT>|n {target} has failed to interrupt {attacker}'s {modifier}{attack} with {interrupt}.\n" \
                      "|-|r** CRITICAL HIT! **|n"
    # 8: Fail to interrupt
    elif action_result == ActionResult.INTERRUPT_FAIL:
        caller.msg("You have failed to interrupt {attack}.".format(attack=attack.name))
        caller.msg("You took {dmg} damage.".format(dmg=round(damage)))
        msg_to_room = "|y<COMBAT>|n {target} has failed to interrupt {attacker}'s {modifier}{attack} with {interrupt}."
    # 9: Successfully interrupt
    elif action_result == ActionResult.INTERRUPT_SUCCESS:
        caller.msg("You interrupt {attack} with {interrupt}.".format(attack=attack.name,
                                                                     interrupt=interrupt.name))
        caller.msg("You took {dmg} damage.".format(dmg=round(mitigated_damage)))
        msg_to_room = "|y<COMBAT>|n {target} interrupts {attacker}'s {modifier}{attack} with {interrupt}."
        interrupted_char.msg("You took {dmg} damage.".format(dmg=round(damage)))
    # 10: Critically succeed at interrupt
    elif action_result == ActionResult.INTERRUPT_CRIT_SUCCESS:
        caller.msg("You critically interrupt {attack} with {interrupt}!".format(attack=attack.name,
                                                                                interrupt=interrupt.name))
        caller.msg("You took {dmg} damage.".format(dmg=round(mitigated_damage)))
        msg_to_room = "|y<COMBAT>|n {target} interrupts {attacker}'s {modifier}{attack} with {interrupt}.\n" \
                      "|-|r** CRITICAL HIT! **|n"
        interrupted_char.msg("You took {dmg} damage.".format(dmg=round(damage)))
    return msg_to_room


def protect_and_reflect_check(incoming_damage, defender, attack, interrupt_success):
    # Protect and Reflect mitigate damage specifically for an interrupter when interrupting.
    if (defender.db.buffs["Protect"] > 0 and attack.stat.lower() == "power") or (defender.db.buffs["Reflect"] > 0 and attack.stat.lower() == "knowledge"):
        if interrupt_success:
            incoming_damage = incoming_damage * 0.75
        else:
            incoming_damage = incoming_damage * 0.85
    return incoming_damage

#TODO: rename all the accuracy vars to "percentage" or something
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
    target.db.debuffs_standard["Poison"] -= 1
    if target.db.debuffs_standard["Poison"] == 0:
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
        # Check if it's now your final_action BECAUSE of the wound damage specifically.
        if character.db.final_action and not initial_state:
            character.db.negative_lf_from_dot = True
        # This check will only be called if Wound's duration is already greater than 1.
    character.db.debuffs_standard["Wound"] -= 1
    if character.db.debuffs_standard["Wound"] == 0:
        character.msg("You are no longer wounded.")


def berserk_check(caller, action):
    # If a character is Berserk, Arts of lower than 50 DMG cost 10 more AP.
    if caller.db.debuffs_standard["Berserk"] > 0:
        if action.dmg < 50:
            action.ap -= 10
    return action


def hex_counter(caller):
    # Making this a separate mini-function for use in both modify_speed and display_status_effects.
    hex_counter = 0
    for duration in caller.db.debuffs_hexes.values():
        if duration > 0:
            hex_counter += 1
    return hex_counter


def clear_hexes(caller):
    # Another separate mini-function for use by CmdPass and the Cure effect.
    for status_effect, duration in caller.db.debuffs_hexes.items():
        if duration > 0:
            caller.db.debuffs_hexes[status_effect] = 0
            caller.msg(f"You are no longer afflicted by {status_effect}.")


def strain_check(attack_damage, attacker):
    # Currently, Strain effectively increases the Damage value of an Art by 1.
    attack_damage = attack_damage + 1
    # Strain's self-damage calculation is a random integer, multiplied by the same damage scale as in damage_calc.
    strain_damage = random.randint(20, 40)
    multiplier = 1.0 - ((6 - attack_damage) * 0.1)
    strain_damage = int(strain_damage * multiplier)
    attacker.db.lf -= strain_damage
    attacker.msg("You have taken {damage} damage from strain.".format(damage=strain_damage))
    initial_state = attacker.db.final_action
    final_action_check(attacker)
    # Check if it's now your final_action BECAUSE of the strain damage specifically.
    if attacker.db.final_action and not initial_state:
        attacker.db.negative_lf_from_dot = True
    # Now that attacker self-damage has been resolved, return the incresaed Damage value of the Art.
    return attack_damage


def modify_ex_on_hit(damage, defender, attacker):
    # Called when 1) a defender fails a reaction and is damaged or 2) fails an interrupt action and is damaged.
    # The damaged character gains a fair amount of EX and the damaging character gains some EX, proportional to damage.
    # Modify EX based on damage taken.
    # Modify the character's EX based on the damage inflicted.
    new_defender_ex = ex_gain_on_defense(damage, defender.db.ex, defender.db.maxex)
    # Modify the attacker's EX based on the damage inflicted.
    new_attacker_ex = ex_gain_on_attack(damage, attacker.db.ex, attacker.db.maxex)
    return new_defender_ex, new_attacker_ex


def modify_ex_on_interrupt_success(mitigated_damage, interrupt_damage, interrupting_char, interrupted_char):
    # Called specifically when a target successfully interrupts. In this case, both characters are damaged by each
    # other's attacks, so EX is gained BY both FOR both damaging and being damaged, proportional to damage.
    # Modify the interrupting character's EX based on the damage dealt AND inflicted.
    interrupting_char_ex = ex_gain_on_defense(mitigated_damage, interrupting_char.db.ex, interrupting_char.db.maxex)
    interrupting_char_ex = ex_gain_on_attack(interrupt_damage, interrupting_char_ex, interrupting_char.db.maxex)

    # Modify the interrupted character's EX based on the damage dealt AND inflicted.
    interrupted_char_ex = ex_gain_on_attack(mitigated_damage, interrupted_char.db.ex, interrupted_char.db.maxex)
    interrupted_char_ex = ex_gain_on_defense(interrupt_damage, interrupted_char_ex, interrupted_char.db.maxex)
    return interrupting_char_ex, interrupted_char_ex


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
                    status_effect_end_message(character, status_effect)
    for status_effect, duration in character.db.debuffs_standard.items():
        if status_effect == "Poison" and duration > 0:
            poison_check(character)
        elif status_effect == "Wound" and duration > 0:
            wound_check(character, action)
        elif duration > 0:
            character.db.debuffs_standard[status_effect] -= 1
            if character.db.debuffs_standard[status_effect] == 0:
                status_effect_end_message(character, status_effect)
    for status_effect, duration in character.db.debuffs_transform.items():
        if duration > 0:
            character.db.debuffs_transform[status_effect] -= 1
            if character.db.debuffs_transform[status_effect] == 0:
                status_effect_end_message(character, status_effect)
    for status_effect, duration in character.db.debuffs_hexes.items():
        if duration > 0:
            character.db.debuffs_hexes[status_effect] -= 1
            if character.db.debuffs_hexes[status_effect] == 0:
                status_effect_end_message(character, status_effect)
    # Base resistance is 0, so for any resistance higher than that, decrease by 10 every tick to floor of 0.
    for resistance in character.db.resistances.keys():
        if character.db.resistances[resistance] > 0:
            character.db.resistances[resistance] -= 10
            # Make sure it can't somehow go below 0
            if character.db.resistances[resistance] < 0:
                character.db.resistances[resistance] = 0


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
                          "Bless": 0, "Purity": 0}
    character.db.debuffs_standard = {"Poison": 0, "Wound": 0, "Curse": 0, "Injure": 0, "Muddle": 0, "Miasma": 0,
                                     "Berserk": 0, "Petrify": 0, "Slime": 0}
    character.db.debuffs_transform = {"Bird": 0, "Frog": 0, "Pig": 0, "Pumpkin": 0}
    character.db.debuffs_hexes = {"Blind": 0, "Silence": 0, "Amnesia": 0, "Sleep": 0, "Charm": 0, "Confuse": 0, "Fear": 0,
                                  "Bind": 0, "Zombie": 0, "Doom": 0, "Dance": 0, "Stinky": 0, "Itchy": 0, "Old": 0}
    character.db.resistances = {"Poison": 0, "Wound": 0, "Curse": 0, "Injure": 0, "Muddle": 0, "Miasma": 0, "Berserk": 0,
                                "Petrify": 0, "Slime": 0, "Bird": 0, "Frog": 0, "Pig": 0, "Pumpkin": 0, "Blind": 0,
                                "Silence": 0, "Amnesia": 0, "Sleep": 0, "Charm": 0, "Confuse": 0, "Fear": 0, "Bind": 0,
                                "Zombie": 0, "Doom": 0, "Dance": 0, "Stinky": 0, "Itchy": 0, "Old": 0}
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
    duration_string = ""
    single_string = ""
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
                duration_string = "You will gradually regenerate for {duration} rounds."
                single_string = "You will gradually regenerate for 1 more round."
            elif status_effect == "Vigor":
                duration_string = "You are invigorated for {duration} rounds."
                single_string = "You are invigorated for 1 more round."
            elif status_effect == "Protect":
                duration_string = "You are protected for {duration} rounds."
                single_string = "You are protected for 1 more round."
            elif status_effect == "Reflect":
                duration_string = "You are reflective for {duration} rounds."
                single_string = "You are reflective for 1 more round."
            elif status_effect == "Acuity":
                duration_string = "You are acutely attentive to critical vulnerabilities for {duration} rounds."
                single_string = "You are acutely attentive to critical vulnerabilities for 1 more round."
            elif status_effect == "Haste":
                duration_string = "You are hastened for {duration} rounds."
                single_string = "You are hastened for 1 more round."
            elif status_effect == "Blink":
                duration_string = "You are trailed by afterimages for {duration} rounds."
                single_string = "You are trailed by afterimages for 1 more round."
            elif status_effect == "Bless":
                duration_string = "Your resistance to debilitating effects is enhanced for {duration} rounds."
                single_string = "Your resistance to debilitating effects is enhanced for 1 more round."
            elif status_effect == "Purity":
                duration_string = "You are purified, rendering you immune to transformation and hexes for {duration} rounds."
                single_string = "You are purified, rendering you immune to transformation and hexes for 1 more round."
        if caller.db.buffs[status_effect] > 1:
            caller.msg(duration_string.format(duration=duration))
        elif caller.db.buffs[status_effect] == 1:
            caller.msg(single_string)
    for status_effect, duration in caller.db.debuffs_standard.items():
        if status_effect == "Poison" and duration > 0:
            duration_string = "You are poisoned and suffering damage over time for {duration} rounds."
            single_string = "You are poisoned and suffering damage over time for 1 more round."
        elif status_effect == "Wound" and duration > 0:
            duration_string = "You are wounded and suffering damage when you exert yourself for {duration} rounds."
            single_string = "You are wounded and suffering damage when you exert yourself for 1 more round."
        elif status_effect == "Curse" and duration > 0:
            duration_string = "You are cursed, increasing your vulnerability to debilitating effects for {duration} rounds."
            single_string = "You are cursed, increasing your vulnerability to debilitating effects for 1 more round."
        elif status_effect == "Injure" and duration > 0:
            duration_string = "You are injured, reducing your effective Power, Parry, and Speed for {duration} rounds."
            single_string = "You are injured, reducing your effective Power, Parry, and Speed for 1 more round."
        elif status_effect == "Muddle" and duration > 0:
            duration_string = "You are muddled, reducing your effective Knowledge, Barrier, and Speed for {duration} rounds."
            single_string = "You are muddled, reducing your effective Knowledge, Barrier, and Speed for 1 more round."
        elif status_effect == "Miasma" and duration > 0:
            duration_string = "You are afflicted by a miasma that halves the effects of healing upon you for {duration} rounds."
            single_string = "You are afflicted by a miasma that halves the effects of healing upon you for 1 more round."
        elif status_effect == "Berserk" and duration > 0:
            duration_string = "You are berserk, increasing your effective Power, Knowledge, and Speed, but also the AP " \
                              "cost of Arts and Normals with a DMG of less than 50, for {duration} rounds."
            single_string = "You are berserk, increasing your effective Power, Knowledge, and Speed, but also the AP " \
                            "cost of Arts and Normals with a DMG of less than 50, for 1 round."
        elif status_effect == "Petrify" and duration > 0:
            duration_string = "You are petrified, reducing your Speed and especially your Dodge chances but somewhat " \
                              "increasing your Block and Endure chances for {duration} rounds."
            single_string = "You are petrified, reducing your Speed and especially your Dodge chances but somewhat " \
                            "increasing your Block and Endure chances for 1 more round."
        elif status_effect == "Slime" and duration > 0:
            duration_string = "You are slimy, reducing your Speed and especially your Block chances but somewhat " \
                              "increasing your Dodge and Endure chances for {duration} rounds."
            single_string = "You are slimy, reducing your Speed and especially your Block chances but somewhat " \
                            "increasing your Dodge and Endure chances for 1 more round."
        if caller.db.debuffs_standard[status_effect] > 1:
            caller.msg(duration_string.format(duration=duration))
        elif caller.db.debuffs_standard[status_effect] == 1:
            caller.msg(single_string)
    for status_effect, duration in caller.db.debuffs_transform.items():
        if status_effect == "Bird" and duration > 0:
            duration_string = "You have been turned into a bird for {duration} rounds."
            single_string = "You have been turned into a bird for 1 more round."
        elif status_effect == "Frog" and duration > 0:
            duration_string = "You have been turned into a frog for {duration} rounds."
            single_string = "You have been turned into a frog for 1 more round."
        elif status_effect == "Pig" and duration > 0:
            duration_string = "You have been turned into a pig for {duration} rounds."
            single_string = "You have been turned into a pig for 1 more round."
        elif status_effect == "Pumpkin" and duration > 0:
            duration_string = "You have been turned into a pumpkin for {duration} rounds."
            single_string = "You have been turned into a pumpkin for 1 more round."
        if caller.db.debuffs_transform[status_effect] > 1:
            caller.msg(duration_string.format(duration=duration))
        elif caller.db.debuffs_transform[status_effect] == 1:
            caller.msg(single_string)
    for status_effect, duration in caller.db.debuffs_hexes.items():
        if status_effect == "Blind" and duration > 0:
            duration_string = "Hex: you are blind for {duration} rounds. RP as though you cannot see."
            single_string = "Hex: you are blind for 1 more round. RP as though you cannot see."
        elif status_effect == "Silence" and duration > 0:
            duration_string = "Hex: you are silenced for {duration} rounds. RP as though you cannot speak."
            single_string = "Hex: you are silenced for 1 more round. RP as though you cannot speak."
        elif status_effect == "Amnesia" and duration > 0:
            duration_string = "Hex: you are suffering from amnesia for {duration} rounds. RP as though you are very forgetful."
            single_string = "Hex: you are suffering from amnesia for 1 more round. RP as though you are very forgetful."
        elif status_effect == "Sleep" and duration > 0:
            duration_string = "Hex: you are drowsy for {duration} rounds. RP as though you are sleepy or sleepwalking."
            single_string = "Hex: you are drowsy for 1 more round. RP as though you are sleepy or sleepwalking."
        elif status_effect == "Charm" and duration > 0:
            duration_string = "Hex: you are charmed for {duration} rounds. RP as though smitten with someone."
            single_string = "Hex: you are charmed for 1 more round. RP as though smitten with someone."
        elif status_effect == "Confuse" and duration > 0:
            duration_string = "Hex: you are confused for {duration} rounds. RP as though you cannot distinguish friend from foe."
            single_string = "Hex: you are confused for 1 more round. RP as though you cannot distinguish friend from foe."
        elif status_effect == "Fear" and duration > 0:
            duration_string = "Hex: you are afraid for {duration} rounds. RP as though stricken with terror."
            single_string = "Hex: you are afraid for 1 more round. RP as though stricken with terror."
        elif status_effect == "Bind" and duration > 0:
            duration_string = "Hex: you are bound for {duration} rounds. RP as though you cannot easily move."
            single_string = "Hex: you are bound for 1 more round. RP as though you cannot easily move."
        elif status_effect == "Zombie" and duration > 0:
            duration_string = "Hex: you are zombified for {duration} rounds. RP this as either literal or psychological."
            single_string = "Hex: you are zombified for 1 more round. RP this as either literal or psychological."
        elif status_effect == "Doom" and duration > 0:
            duration_string = "Hex: you are doomed for {duration} rounds. RP as though having an existential crisis."
            single_string = "Hex: you are doomed for 1 more round. RP as though having an existential crisis."
        elif status_effect == "Dance" and duration > 0:
            duration_string = "Hex: you are compelled to dance for {duration} rounds. RP as though you must groove."
            single_string = "Hex: you are compelled to dance for 1 more round. RP as though you must groove."
        elif status_effect == "Stinky" and duration > 0:
            duration_string = "Hex: you are stinky for {duration} rounds. RP as though you reek of a terrible stench."
            single_string = "Hex: you are stinky for 1 more round. RP as though you reek of a terrible stench."
        elif status_effect == "Itchy" and duration > 0:
            duration_string = "Hex: you are itchy for {duration} rounds. RP as though compelled to scratch."
            single_string = "Hex: you are itchy for 1 more round. RP as though compelled to scratch."
        elif status_effect == "Old" and duration > 0:
            duration_string = "Hex: you are aged for {duration} rounds. RP as though you have considerably aged."
            single_string = "Hex: you are aged for 1 more round. RP as though you have considerably aged."
        if caller.db.debuffs_hexes[status_effect] > 1:
            caller.msg(duration_string.format(duration=duration))
        elif caller.db.debuffs_hexes[status_effect] == 1:
            caller.msg(single_string)
    # End with a hex summary
    hex_count = hex_counter(caller)
    if hex_count > 0:
        if hex_count > 1:
            intensity_string = ""
            if hex_count == 2:
                intensity_string = "moderately"
            elif hex_count == 3:
                intensity_string = "severely"
            else:
                intensity_string = "grievously"
            caller.msg(f"Your {hex_count} hexes {intensity_string} reduce your effective Speed. "
                       f"'Pass' or Cure clears hexes.")
        else:
            # Hex_count is exactly 1
            caller.msg("Your hex slightly reduces your effective Speed. 'Pass' or Cure clears hexes.")



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
        elif buff == "Purity":
            application_string = "You are purified, rendering you immune to transformation and hexes."
            extension_string = "The duration of your purification has been extended."
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
    if target.db.debuffs_standard["Curse"] > 0:
        base_debuff_resist -= 20
    application_string = ""
    extension_string = ""
    debuff_effects = []
    morph = False
    random_hexes_to_apply = 0
    # Find all the effects on the action that are debuffs.
    split_effect_list = action.effects.split()
    for effect in split_effect_list:
        for debuff in DEBUFFS:
            if effect == "Hex1":
                random_hexes_to_apply = 1
            elif effect == "Hex2":
                random_hexes_to_apply = 2
            elif effect == "Hex3":
                random_hexes_to_apply = 3
            elif effect == "Morph":
                morph = True
            # Designing this so that Hex1, Hex2, Hex3, and Morph do not themselves get added to debuff_effects.
            elif effect == debuff.name:
                debuff_effects.append(effect)
    # Loop through the hexes as much as required, randomizing which ones to add, never duplicating.
    while random_hexes_to_apply:
        # Add additional random hexes that are not already one of the Art's effects.
        hex_options = []
        for hex in DEBUFFS_HEXES:
            if hex.name not in debuff_effects:
                hex_options.append(hex.name)
        debuff_effects.append(random.choice(hex_options))
        random_hexes_to_apply -= 1
    if morph:
        morph_options = []
        # It would be weird to have an Art with both Morph and another transformation debuff, but possible!
        for transformation in DEBUFFS_TRANSFORMATION:
            if transformation.name not in debuff_effects:
                morph_options.append(transformation.name)
        debuff_effects.append(random.choice(morph_options))
    # Now prepare debuff strings and roll the check against the appropriate resistance.
    for debuff in debuff_effects:
        # Find resistance in target.db.resistances
        debuff_resist = base_debuff_resist + target.db.resistances[debuff]
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
                                 "increasing the cost of using less damaging, more accurate attacks."
            extension_string = "The duration of your berserk fury has been extended."
        elif debuff == "Petrify":
            application_string = "You are petrified, reducing your Speed and especially your Dodge chances but " \
                                 "somewhat increasing your Block and Endure chances."
            extension_string = "The duration of your petrifaction has been extended."
        elif debuff == "Slime":
            application_string = "You are slimy, reducing your Speed and especially your Block chances but somewhat " \
                                 "increasing your Dodge and Endure chances."
            extension_string = "The duration of your sliminess has been extended."
        elif debuff == "Bird":
            application_string = "You have been turned into a bird, effectively halving your Power and Parry."
            extension_string = "The duration of your transformation to a bird has been extended."
        elif debuff == "Frog":
            application_string = "You have been turned into a frog, effectively halving your Power and Barrier."
            extension_string = "The duration of your transformation to a frog has been extended."
        elif debuff == "Pig":
            application_string = "You have been turned into a pig, effectively halving your Knowledge and Parry."
            extension_string = "The duration of your transformation to a pig has been extended."
        elif debuff == "Pumpkin":
            application_string = "You have been turned into a pumpkin, effectively halving your Knowledge and Barrier."
            extension_string = "The duration of your transformation to a pumpkin has been extended."
        elif debuff == "Blind":
            application_string = "You are hexed to be blind. RP as though you cannot see."
            extension_string = "The duration of your blindness has been extended."
        elif debuff == "Silence":
            application_string = "You are hexed to be silent. RP as though you cannot speak."
            extension_string = "The duration of your silence has been extended."
        elif debuff == "Amnesia":
            application_string = "You are hexed with amnesia. RP as though you are very forgetful."
            extension_string = "The duration of your amnesia has been extended."
        elif debuff == "Sleep":
            application_string = "You are hexed with drowsiness. RP as though you are sleepy or sleepwalking."
            extension_string = "The duration of your drowsiness has been extended."
        elif debuff == "Charmed":
            application_string = "You are hexed to be charmed. RP as though smitten with someone."
            extension_string = "The duration of your charmed state has been extended."
        elif debuff == "Confuse":
            application_string = "You are hexed to be confused. RP as though you cannot distinguish friend from foe."
            extension_string = "The duration of your confusion has been extended."
        elif debuff == "Fear":
            application_string = "You are hexed to be afraid. RP as though stricken with terror."
            extension_string = "The duration of your fear has been extended."
        elif debuff == "Bind":
            application_string = "You are hexed to be bound. RP as though you cannot easily move."
            extension_string = "The duration of your binding has been extended."
        elif debuff == "Zombie":
            application_string = "You are hexed to be zombified. RP this as either literal or psychological."
            extension_string = "The duration of your zombification has been extended."
        elif debuff == "Doom":
            application_string = "You are hexed to be doomed. RP as though having an existential crisis."
            extension_string = "The duration of your doomed state has been extended."
        elif debuff == "Dance":
            application_string = "You are hexed to dance. RP as though compelled to groove."
            extension_string = "The duration of your compulsion to dance has been extended."
        elif debuff == "Stinky":
            application_string = "You are hexed to be stinky. RP as though you reek of a terrible stench."
            extension_string = "The duration of your stench has been extended."
        elif debuff == "Itchy":
            application_string = "You are hexed to be itchy. RP as though compelled to scratch."
            extension_string = "The duration of your transformation to a bird has been extended."
        elif debuff == "Old":
            application_string = "You are hexed to be old. RP as though you have considerably aged."
            extension_string = "The duration of your aged state has been extended."
        # Roll the debuff check
        debuff_check_roll = random.randint(1, 100)
        # I hope I'm not being too cute here: if Purity is active and debuff is transform/hex, set roll to -1 to fail.
        if target.db.buffs["Purity"] > 0:
            if debuff not in target.db.debuffs_standard.keys():
                debuff_check_roll = -1
                # If the debuff isn't in debuffs_standard, it must be in debuffs_transform or debuffs_hexes.
        if debuff_check_roll > debuff_resist:
            # If debuff succeeds, apply using consistent logic. Check what dict the debuff is stored in
            if debuff in target.db.debuffs_standard.keys():
                if target.db.debuffs_standard[debuff] == 0:
                    target.msg(application_string)
                else:
                    target.msg(extension_string)
                target.db.debuffs_standard[debuff] = 3
                # For standard debuffs, increase the resistance to that debuff by 40.
                target.db.resistances[debuff] += 30
            elif debuff in target.db.debuffs_transform.keys():
                if target.db.debuffs_transform[debuff] == 0:
                    target.msg(application_string)
                else:
                    target.msg(extension_string)
                target.db.debuffs_transform[debuff] = 2
                # Because a character can only be transformed in one way, any other transformation is negated.
                for transformation, duration in target.db.debuffs_transform.items():
                    if transformation != debuff and duration > 0:
                        target.db.debuffs_transform[transformation] = 0
                        status_effect_end_message(target, transformation)
                # For transformation debuffs, increase the resistance to that debuff by 60 and all others by 40.
                target.db.resistances[debuff] += 20
                for transformation in target.db.debuffs_transform.keys():
                    target.db.resistances[transformation] += 40
            elif debuff in target.db.debuffs_hexes.keys():
                if target.db.debuffs_hexes[debuff] == 0:
                    target.msg(application_string)
                else:
                    target.msg(extension_string)
                target.db.debuffs_hexes[debuff] = 3
                # For hexes, increase the resistance to that hex by 40 and all others by 20.
                target.db.resistances[debuff] += 20
                for hex in target.db.debuffs_hexes.keys():
                    target.db.resistances[hex] += 20


def status_effect_end_message(character, status_effect):
    # Writing a separate sub-function for when status effects end to be called both by combat_tick and heal_check
    # for when Cure is used, so I don't have to write redundant strings for the "effect ends" message.
    # Note that this function exclusively sends messages. It does not modify status effect durations.
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
    elif status_effect == "Purity":
        character.msg("You are no longer immune to transformation or hexes.")
    elif status_effect == "Curse":
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
    elif status_effect == "Slime":
        character.msg("You are no longer slimy.")
    elif status_effect == "Bird":
        character.msg("You are no longer a bird.")
    elif status_effect == "Frog":
        character.msg("You are no longer a frog.")
    elif status_effect == "Pig":
        character.msg("You are no longer a pig.")
    elif status_effect == "Pumpkin":
        character.msg("You are no longer a pumpkin.")
    elif status_effect == "Blind":
        character.msg("You are no longer blind.")
    elif status_effect == "Silence":
        character.msg("You are no longer silenced.")
    elif status_effect == "Amnesia":
        character.msg("You are no longer suffering from amnesia.")
    elif status_effect == "Sleep":
        character.msg("You are no longer drowsy.")
    elif status_effect == "Charm":
        character.msg("You are no longer charmed.")
    elif status_effect == "Confuse":
        character.msg("You are no longer confused.")
    elif status_effect == "Fear":
        character.msg("You are no longer afraid.")
    elif status_effect == "Bind":
        character.msg("You are no longer bound.")
    elif status_effect == "Zombie":
        character.msg("You are no longer zombified.")
    elif status_effect == "Doom":
        character.msg("You are no longer doomed.")
    elif status_effect == "Dance":
        character.msg("You are no longer compelled to dance.")
    elif status_effect == "Stinky":
        character.msg("You are no longer stinky.")
    elif status_effect == "Itchy":
        character.msg("You are no longer itchy.")
    elif status_effect == "Old":
        character.msg("You are no longer aged.")