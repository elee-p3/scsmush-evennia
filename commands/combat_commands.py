from world.combat.normals import NORMALS
from evennia import default_cmds
from world.utilities.utilities import *
import random
from world.combat.combat_functions import *
from world.combat.effects import AimOrFeint
from math import floor, ceil
import copy
from world.combat.attacks import AttackInstance


# def append_to_queue(target, attack, attacker, aim_or_feint):
#     # TODO: create class for queue_object instead of a dict
    # append a tuple per attack: (id, attack)
    # theoretically, you should always resolve all attacks in your queue before having more people attack you
    # this code should always just tack on at the end of the list even if that doesn't happen
    # if not target.db.queue:
    #     last_id = 0
    # else:
    #     last_id = max((attack["id"] for attack in target.db.queue))
    # target.db.queue.append({"id":last_id+1, "attack":attack_object, "modified_damage":attack_damage, "modified_accuracy":
    #     modified_accuracy, "attacker":attacker, "aim_or_feint":aim_or_feint})
    # target.db.queue.append({"id":last_id+1, "attack":attack, "attacker":attacker, "aim_or_feint":aim_or_feint})
    # target.db.queue.append({"id": last_id + 1, "attack": attack, "attacker": attacker, "aim_or_feint": aim_or_feint})


def display_queue(caller):
    # This function is called by both the "queue" command and by "check" when input without arguments.
    if not caller.db.queue:
        caller.msg("Nothing in queue.")
    else:
        for atk_obj in caller.db.queue:
            attack = atk_obj.attack
            id = atk_obj.id
            accuracy = attack.acc
            weave_boole = False
            brace_boole = False
            crush_boole = False
            sweep_boole = False
            rush_boole = False
            # Checking for persistent status effects on the defender.
            if caller.db.is_weaving:
                weave_boole = True
            if caller.db.is_bracing:
                brace_boole = True
            if caller.db.is_rushing:
                rush_boole = True
            if atk_obj.has_crush:
                crush_boole = True
            if atk_obj.has_sweep:
                sweep_boole = True
            # Checking for block penalty.
            block_penalty = caller.db.block_penalty
            modified_acc_for_dodge = dodge_calc(accuracy, caller.db.speed, sweep_boole, weave_boole, rush_boole)
            dodge_pct = 100 - modified_acc_for_dodge
            modified_acc_for_block = block_chance_calc(accuracy, attack.base_stat, caller.db.speed,
                                                       caller.db.parry, caller.db.barrier, crush_boole,
                                                       brace_boole, block_penalty, rush_boole)
            block_pct = 100 - modified_acc_for_block
            modified_acc_for_endure = endure_chance_calc(accuracy, attack.base_stat, caller.db.speed,
                                                         caller.db.parry, caller.db.barrier, brace_boole, rush_boole)
            endure_pct = 100 - modified_acc_for_endure
            # TODO: replace this string with evtable?
            caller.msg("{0}. {1} -- {2} -- D: {3}% B: {4}% E: {5}%".format(id, attack.name, attack.base_stat,
                                                                           round(dodge_pct), round(block_pct),
                                                                           round(endure_pct)))


class CmdAttack(default_cmds.MuxCommand):
    """
        Combat command. Use to attack an opponent during combat.

        The "target" must be the name of another character to receive the attack.

        The "action" must be the name of the attack your character will use.
        This must be either a Normal or Art possessed by your character.
        Type "attacks" to see all attacks available.

        Usage:
          +attack target=action

    """

    key = "+attack"
    aliases = ["attack"]
    locks = "cmd:all()"

    def func(self):
        # Attack should take two arguments: a target and an attack name
        # Format should be "attack x=y" where x is target and y is attack
        caller = self.caller
        location = caller.location
        args = self.args
        arts = caller.db.arts

        if len(args) == 0:
            return caller.msg("You need to specify a target and action. See `help attack` for syntax.")

        split_args = args.split('=')

        if len(split_args) != 2:
            return caller.msg("Unrecognized command syntax. See `help attack`.")

        target = split_args[0].lower() # make everything case-insensitive
        action = split_args[1].lower()

        aim_or_feint = AimOrFeint.NEUTRAL
        if caller.db.is_aiming:
            aim_or_feint = AimOrFeint.AIM
        if caller.db.is_feinting:
            aim_or_feint = AimOrFeint.FEINT
        # caller.msg(target)
        # caller.msg(action)

        # First, check that the character attacking is not KOed
        if caller.db.KOed:
            return caller.msg("Your character is KOed and cannot act.")

        # Then check that the target is a character in the room using utility
        characters_in_room = location_character_search(location)
        # Check aliases of characters in room as well
        alias_list_in_room = [(character, character.aliases.all()) for character in characters_in_room]
        target_alias_list = [idx for idx, alias_tuple in enumerate(alias_list_in_room) if target.lower() in alias_tuple[1]]

        target_object = None
        if target_alias_list:
            target_alias_idx = target_alias_list[0]
            target_object = alias_list_in_room[target_alias_idx][0]

        if target not in [character.name.lower() for character in characters_in_room]:
            if not target_object:
                return caller.msg("Your target is not a character in this room.")

        # Find the actual character object using the input string
        for obj in location.contents:
            if not target_object:
                if target in obj.db_key.lower():
                    target_object = obj

        # Now check that the action is an attack.
        if action not in NORMALS:
            if action not in arts:
                return caller.msg("Your selected action cannot be found.")
        if action in NORMALS:
            action_clean = NORMALS[NORMALS.index(action)]    # found action with correct capitalization
        else:
            action_clean = arts[arts.index(action)]

        # If the target is here and the action exists, then we add the attack to the target's queue.
        # The attack should be assigned an ID based on its place in the queue.
        # Check if the "queue" attribute exists and, if not, create an empty list first.
        if target_object.db.queue is None:
            target_object.db.queue = []

        # Modify the damage and accuracy of the attack based on our combat functions.
        # Copy.copy is used to ensure we do not modify the attack in the character's list, just this instance of it.
        action_clean = copy.copy(action_clean)
        action_clean.dmg = modify_damage(action_clean, caller)
        action_clean.acc = modify_accuracy(action_clean, caller)

        # If the character has insufficient AP or EX to use that move, cancel the attack.
        # Otherwise, set their EX from 100 to 0.
        total_ap_change = action_clean.ap_change
        if caller.db.is_aiming or caller.db.is_feinting:
            total_ap_change -= 10
        if caller.db.ap + total_ap_change < 0:
            return caller.msg("You do not have enough AP to do that.")
        if "EX" in action_clean.effects:
            if caller.db.ex - 100 < 0:
                return caller.msg("You do not have enough EX to do that.")
            caller.db.ex = 0
        # If the character has insufficient EX to use that move, cancel the attack.
        # Modify the character's AP based on the attack's AP cost.
        caller.db.ap += total_ap_change

        # The attack is now confirmed. First, "tick" to have a round pass, progressing/clearing prior status effects.
        combat_tick(caller)

        # Now apply any persistent effects that will affect the attacker regardless of the attack's future success.
        caller = apply_attack_effects_to_attacker(caller, action_clean)

        # Append the attack to the target's queue and announce the attack.
        # if caller.db.is_aiming:
        #     append_to_queue(target_object, action_clean, caller, AimOrFeint.AIM)
        # elif caller.db.is_feinting:
        #     append_to_queue(target_object, action_clean, caller, AimOrFeint.FEINT)
        # else:
        #     append_to_queue(target_object, action_clean, caller, AimOrFeint.NEUTRAL)

        new_id = assign_attack_instance_id(target_object)
        target_object.db.queue.append(AttackInstance(new_id, action_clean, caller.key, aim_or_feint))

        caller.msg("You attacked {target} with {action}.".format(target=target_object, action=action_clean))
        combat_string = "|y<COMBAT>|n {attacker} has attacked {target} with {action}.".format(
            attacker=caller.key, target=target_object, action=action_clean)
        caller.location.msg_contents(combat_string)
        # TODO: when we generalize the log_entry function, replace all combat_log_entry with that + combat parameter
        combat_log_entry(caller, combat_string)

        caller.db.is_aiming = False
        caller.db.is_feinting = False
        # If this was the attacker's final action, they are now KOed.
        if caller.db.final_action:
            caller.db.final_action = False
            caller.db.KOed = True
            caller.msg("You have taken your final action and can no longer fight.")
            combat_string = "|y<COMBAT>|n {0} can no longer fight.".format(caller.name)
            caller.location.msg_contents(combat_string)
            # TODO: replace
            combat_log_entry(caller, combat_string)


class CmdQueue(default_cmds.MuxCommand):
    # TODO: Replace both queue and check without arguments with a shared function using evtable?
    """
        Combat command. View all incoming attacks in your character's queue.
        Unlike the "check" command, this does not display additional information, such as status effects.

        Usage:
          +queue

    """

    key = "+queue"
    aliases = ["queue"]
    locks = "cmd:all()"

    # The queue command prints the attacks that you have been targeted with.
    # You are not allowed to attack until you've dealt with your queue.
    # Reaction commands remove attacks from your queue and resolve them.

    def func(self):
        caller = self.caller
        display_queue(caller)


class CmdDodge(default_cmds.MuxCommand):
    """
        A combat reaction. Attempt to dodge an attack, fully negating its damage.

        Usage:
          +dodge <queue id>

    """

    key = "+dodge"
    aliases = ["dodge"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        id_list = [attack.id for attack in caller.db.queue]

        # Syntax is just "dodge <id>".
        if not args.isdigit():
            return caller.msg("Please input the attack ID as an integer.")

        input_id = int(args)

        if input_id not in id_list:
            return caller.msg("Cannot find that attack in your queue.")

        # The attack is an Attack object in the queue. Roll the die and remove the attack from the queue.
        action = caller.db.queue[id_list.index(input_id)]
        attack = action.attack
        attack_damage = attack.dmg
        accuracy = attack.acc
        attacker = find_attacker_from_key(action.attacker_key)
        aim_or_feint = action.aim_or_feint
        modifier = action.modifier
        random100 = random.randint(1, 100)
        sweep_boole = False
        weave_boole = False
        rush_boole = False
        # TODO: take these instances where reactions check for effects and create a meta "check for effects" function
        # where, depending on which reaction it is, different effects are checked for. This will make it easier to
        # modify what effects reactions will check for when I add new effects, instead of having to go to the reaction.
        # Checking if the attack has the Sweep effect.
        if hasattr(attack, "has_sweep"):
            if attack.has_sweep:
                sweep_boole = True
        # Checking if the defender's previous attack had the Weave or Rush effects.
        if caller.db.is_weaving:
            weave_boole = True
        if caller.db.is_rushing:
            rush_boole = True
        modified_acc = dodge_calc(accuracy, caller.db.speed, sweep_boole, weave_boole, rush_boole)

        # do the aiming/feinting modification here since we don't want to show the modified value in the queue
        if aim_or_feint == AimOrFeint.AIM:
            modified_acc += 15
        elif aim_or_feint == AimOrFeint.FEINT:
            modified_acc -= 15

        msg = ""
        is_glancing_blow = False
        attacker_stat = find_attacker_stat(attacker, attack.base_stat)
        if modified_acc > random100:
            # Since the attack has hit, check for glancing blow.
            # attack_with_effects = check_for_effects(attack)
            sweep_boolean = hasattr(attack, "has_sweep")
            is_glancing_blow = glancing_blow_calc(random100, modified_acc, sweep_boolean)
            if is_glancing_blow:
                # For now, halving the damage of glancing blows.
                final_damage = damage_calc(attack_damage, attacker_stat, attack.base_stat, caller.db.parry, caller.db.barrier) / 2
                caller.msg("You have been glanced by {attack}.".format(attack=attack.name))
                caller.msg("You took {dmg} damage.".format(dmg=round(final_damage)))
            else:
                final_damage = damage_calc(attack_damage, attacker_stat, attack.base_stat, caller.db.parry, caller.db.barrier)
                caller.msg("You have been hit by {attack}.".format(attack=attack.name))
                caller.msg("You took {dmg} damage.".format(dmg=round(final_damage)))

            msg = "|y<COMBAT>|n {target} has been hit by {attacker}'s {modifier}{attack}."

            caller.db.lf -= final_damage
            # Modify EX based on damage taken.
            # Modify the character's EX based on the damage inflicted.
            new_ex = ex_gain_on_defense(final_damage, caller.db.ex, caller.db.maxex)
            caller.db.ex = new_ex
            # Modify the attacker's EX based on the damage inflicted.
            new_attacker_ex = ex_gain_on_attack(final_damage, attacker.db.ex, attacker.db.maxex)
            attacker.db.ex = new_attacker_ex
        else:
            caller.msg("You have successfully dodged {attack}.".format(attack=attack.name))
            msg = "|y<COMBAT>|n {target} has dodged {attacker}'s {modifier}{attack}."

        combat_string = msg.format(target=caller.key, attacker=attacker.key, modifier=modifier, attack=attack.name)
        caller.location.msg_contents(combat_string)
        combat_log_entry(caller, combat_string)
        # To avoid overcomplicating the above messaging code, I'm adding the "glancing blow"
        # location message as an additional separate string.
        if is_glancing_blow:
            # TODO: as is, this creates an additional combat log entry for the glancing blow announcement. combine?
            combat_string = "|y<COMBAT>|n ** Glancing Blow **"
            caller.location.msg_contents(combat_string)
            combat_log_entry(caller, combat_string)
        # Checking after the combat location messages if the attack has put the defender at 0 LF or below.
        caller = final_action_check(caller)
        del caller.db.queue[id_list.index(input_id)]


class CmdBlock(default_cmds.MuxCommand):
    """
        A combat reaction. Attempt to block an attack, partially negating its damage.

        Usage:
          +block <queue id>

    """

    key = "+block"
    aliases = ["block"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        id_list = [attack.id for attack in caller.db.queue]

        # Syntax is just "block <id>".
        if not args.isdigit():
            return caller.msg("Please input the attack ID as an integer.")

        input_id = int(args)

        if input_id not in id_list:
            return caller.msg("Cannot find that attack in your queue.")

        # The attack is a string in the queue. Roll the die and remove the attack from the queue.
        action = caller.db.queue[id_list.index(input_id)]
        attack = action.attack
        attack_damage = attack.dmg
        accuracy = attack.acc
        attacker = find_attacker_from_key(action.attacker_key)
        aim_or_feint = action.aim_or_feint
        modifier = action.modifier
        random100 = random.randint(1, 100)
        crush_boole = False
        brace_boole = False
        rush_boole = False
        # attack_with_effects = check_for_effects(attack)
        if hasattr(attack, "has_crush"):
            if attack.has_crush:
                crush_boole = True
        if caller.db.is_bracing:
            brace_boole = True
        if caller.db.is_rushing:
            rush_boole = True
        # Checking for block penalty.
        block_penalty = caller.db.block_penalty
        # Find the attacker's relevant attack stat for damage_calc.
        attacker_stat = find_attacker_stat(attacker, attack.base_stat)
        modified_acc = block_chance_calc(accuracy, attack.base_stat, caller.db.speed, caller.db.parry,
                                         caller.db.barrier, crush_boole, brace_boole, block_penalty, rush_boole)
        modified_damage = damage_calc(attack_damage, attacker_stat, attack.base_stat, caller.db.parry, caller.db.barrier)
        # caller.msg("Base damage is: " + str(attack.dmg))
        # caller.msg("Modified damage is: " + str(modified_damage))

        # do the aiming/feinting modification here since we don't want to show the modified value in the queue
        if aim_or_feint == AimOrFeint.AIM:
            modified_acc += 15
        elif aim_or_feint == AimOrFeint.FEINT:
            modified_acc -= 15

        msg = ""

        if modified_acc > random100:
            caller.msg("You have been hit by {attack}.".format(attack=attack.name))
            caller.msg("You took {dmg} damage.".format(dmg=round(modified_damage)))
            caller.db.lf -= modified_damage

            msg = "|y<COMBAT>|n {target} has been hit by {attacker}'s {modifier}{attack}."

            # Modify the character's EX based on the damage inflicted.
            new_ex = ex_gain_on_defense(modified_damage, caller.db.ex, caller.db.maxex)
            caller.db.ex = new_ex
            # Modify the attacker's EX based on the damage inflicted.
            new_attacker_ex = ex_gain_on_attack(modified_damage, attacker.db.ex, attacker.db.maxex)
            attacker.db.ex = new_attacker_ex
            # Modify the defender's block penalty (a little, since the block failed).
            block_boole = False
            new_block_penalty = accrue_block_penalty(caller, modified_damage, block_boole, crush_boole)
            caller.db.block_penalty = new_block_penalty
        else:
            final_damage = block_damage_calc(modified_damage, block_penalty)
            caller.msg("You have successfully blocked {attack}.".format(attack=attack.name))
            caller.msg("You took {dmg} damage.".format(dmg=round(final_damage)))
            caller.db.lf -= final_damage

            msg = "|y<COMBAT>|n {target} has blocked {attacker}'s {modifier}{attack}."

            # Modify the character's EX based on the damage inflicted.
            new_ex = ex_gain_on_defense(final_damage, caller.db.ex, caller.db.maxex)
            caller.db.ex = new_ex
            # Modify the attacker's EX based on the damage inflicted.
            new_attacker_ex = ex_gain_on_attack(final_damage, attacker.db.ex, attacker.db.maxex)
            attacker.db.ex = new_attacker_ex
            # Modify the defender's block penalty (a lot, since the block succeeded). Based on modified, not final, dmg.
            block_boole = True
            new_block_penalty = accrue_block_penalty(caller, modified_damage, block_boole, crush_boole)
            caller.db.block_penalty = new_block_penalty
        combat_string = msg.format(target=caller.key, attacker=attacker.key, modifier=modifier, attack=attack.name)
        caller.location.msg_contents(combat_string)
        combat_log_entry(caller, combat_string)
        # Checking after the combat location message if the attack has put the defender at 0 LF or below.
        caller = final_action_check(caller)
        del caller.db.queue[id_list.index(input_id)]


class CmdEndure(default_cmds.MuxCommand):
    """
            A combat reaction. Attempt to endure an attack, taking full damage but
            gaining a bonus to the accuracy of your next attack.

            Usage:
              +endure <queue id>

        """

    key = "+endure"
    aliases = ["endure"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        id_list = [attack.id for attack in caller.db.queue]

        # Syntax is just "endure <id>".
        if not args.isdigit():
            return caller.msg("Please input the attack ID as an integer.")

        input_id = int(args)

        if input_id not in id_list:
            return caller.msg("Cannot find that attack in your queue.")

        # The attack is an Attack object in the queue. Roll the die and remove the attack from the queue.
        action = caller.db.queue[id_list.index(input_id)]
        attack = action.attack
        attack_damage = attack.dmg
        accuracy = attack.acc
        attacker = find_attacker_from_key(action.attacker_key)
        aim_or_feint = action.aim_or_feint
        modifier = action.modifier
        random100 = random.randint(1, 100)
        brace_boole = False
        rush_boole = False
        # Checking if the defender's previous attack had the Brace or Rush effect.
        if caller.db.is_bracing:
            brace_boole = True
        if caller.db.is_rushing:
            rush_boole = True
        modified_acc = endure_chance_calc(accuracy, attack.base_stat, caller.db.speed, caller.db.parry, caller.db.barrier,
                                          brace_boole, rush_boole)

        # do the aiming/feinting modification here since we don't want to show the modified value in the queue
        if aim_or_feint == AimOrFeint.AIM:
            modified_acc -= 15
        elif aim_or_feint == AimOrFeint.FEINT:
            modified_acc += 15

        msg = ""
        attacker_stat = find_attacker_stat(attacker, attack.base_stat)
        final_damage = damage_calc(attack_damage, attacker_stat, attack.base_stat, caller.db.parry, caller.db.barrier)
        if modified_acc > random100:
            caller.msg("You have been hit by {attack}.".format(attack=attack.name))
            caller.msg("You took {dmg} damage.".format(dmg=round(final_damage)))
            msg = "|y<COMBAT>|n {target} has been hit by {attacker}'s {modifier}{attack}."
        else:
            caller.msg("You endure {attack}.".format(attack=attack.name))
            caller.msg("You took {dmg} damage.".format(dmg=round(final_damage)))
            msg = "|y<COMBAT>|n {target} endures {attacker}'s {modifier}{attack}."
            # Now calculate endure bonus. Currently, let's set it so if you endure multiple attacks in a round,
            # you get to keep whatever endure bonus is higher. But endure bonus is not cumulative. (That's OP.)
            if endure_bonus_calc(final_damage) > caller.db.endure_bonus:
                caller.db.endure_bonus = endure_bonus_calc(final_damage)

        caller.db.lf -= final_damage
        # Modify EX based on damage taken.
        # Modify the character's EX based on the damage inflicted.
        new_ex = ex_gain_on_defense(final_damage, caller.db.ex, caller.db.maxex)
        caller.db.ex = new_ex
        # Modify the attacker's EX based on the damage inflicted.
        new_attacker_ex = ex_gain_on_attack(final_damage, attacker.db.ex, attacker.db.maxex)
        attacker.db.ex = new_attacker_ex

        combat_string = msg.format(target=caller.key, attacker=attacker.key, modifier=modifier, attack=attack.name)
        caller.location.msg_contents(combat_string)
        combat_log_entry(caller, combat_string)
        # Checking after the combat location messages if the attack has put the defender at 0 LF or below.
        caller = final_action_check(caller)
        del caller.db.queue[id_list.index(input_id)]


class CmdInterrupt(default_cmds.MuxCommand):
    """
            A combat reaction. Attempt to an interrupt an attack with one of your own.
            If successful, your opponent is struck directly, without a chance to react.
            Unlike other reactions, the success of your interrupt depends on the accuracy
            of the attack with which you interrupt, not your Speed.

            However, note that an interrupt is considered both an action and a reaction.
            Whether you succeed or fail, an interrupt constitutes your turn. After you pose,
            your turn is over.

            Usage:
              +interrupt <queue id>=<name of attack>

        """

    key = "+interrupt"
    aliases = ["interrupt"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        arts = caller.db.arts
        id_list = [attack.id for attack in caller.db.queue]
        # Like +attack, +interrupt requires two arguments: a incoming attack and an outgoing interrupt.
        if "=" not in args:
            return caller.msg("Please use proper syntax: interrupt <id>=<name of interrupt>.")
        split_args = args.split("=")
        incoming_attack_arg = split_args[0]
        outgoing_interrupt_arg = split_args[1].lower()

        # Syntax of the first argument is "interrupt <id>".
        if not incoming_attack_arg.isdigit():
            return caller.msg("Please input the attack ID as an integer.")

        if int(incoming_attack_arg) not in id_list:
            return caller.msg("Cannot find that attack in your queue.")

        # Make sure that the outgoing interrupt is an available Art/Normal.
        interrupt_clean = None  # this will be an Attack object
        if outgoing_interrupt_arg not in NORMALS:
            if outgoing_interrupt_arg not in arts:
                return caller.msg("Your selected interrupt action cannot be found.")
        if outgoing_interrupt_arg in NORMALS:
            interrupt_clean = NORMALS[NORMALS.index(outgoing_interrupt_arg)]  # found action with correct capitalization
        else:
            interrupt_clean = arts[arts.index(outgoing_interrupt_arg)]
        # If the character has insufficient AP or EX to use that move, cancel the interrupt.
        # Otherwise, if EX move, set their EX from 100 to 0.
        total_ap_change = interrupt_clean.ap_change
        if caller.db.ap + total_ap_change < 0:
            return caller.msg("You do not have enough AP to do that.")
        if "EX" in interrupt_clean.effects:
            if caller.db.ex - 100 < 0:
                return caller.msg("You do not have enough EX to do that.")
            caller.db.ex = 0
        caller.db.ap += total_ap_change

        # The attack is an Attack object in the queue. Roll the die and remove the attack from the queue.
        incoming_action = caller.db.queue[id_list.index(int(incoming_attack_arg))]
        incoming_attack = incoming_action.attack
        incoming_damage = incoming_attack.dmg
        incoming_accuracy = incoming_attack.acc
        attacker = find_attacker_from_key(incoming_action.attacker_key)
        aim_or_feint = incoming_action.aim_or_feint
        modifier = incoming_action.modifier
        outgoing_interrupt = interrupt_clean
        outgoing_damage = interrupt_clean.dmg
        outgoing_accuracy = interrupt_clean.acc
        random100 = random.randint(1, 100)
        bait_boole = False
        rush_boole = False
        incoming_priority_boole = False
        outgoing_priority_boole = False
        incoming_attack_stat = find_attacker_stat(attacker, incoming_attack.base_stat)
        outgoing_interrupt_stat = find_attacker_stat(caller, outgoing_interrupt.base_stat)
        # Checking if the attacker's attack has the Priority effect.
        if hasattr(incoming_attack, "has_priority"):
            if incoming_attack.has_priority:
                incoming_priority_boole = True
        # Checking if the defender's previous attack had the Bait or Rush effect.
        if caller.db.is_baiting:
            bait_boole = True
        if caller.db.is_rushing:
            rush_boole = True
        # Checking if the defender's interrupt has the Priority effect.
        if hasattr(outgoing_interrupt, "has_priority"):
            if outgoing_interrupt.has_priority:
                outgoing_priority_boole = True
        modified_acc = interrupt_chance_calc(incoming_accuracy, outgoing_accuracy, bait_boole, rush_boole,
                                             incoming_priority_boole, outgoing_priority_boole)

        # do the aiming/feinting modification here since we don't want to show the modified value in the queue
        if aim_or_feint == AimOrFeint.AIM:
            modified_acc -= 15
        elif aim_or_feint == AimOrFeint.FEINT:
            modified_acc += 15

        msg = ""
        if modified_acc > random100:
            # attack_with_effects = check_for_effects(attack)
            final_damage = damage_calc(incoming_damage, incoming_attack_stat, incoming_attack.base_stat, caller.db.parry, caller.db.barrier)
            caller.msg("You have failed to interrupt {attack}.".format(attack=incoming_attack.name))
            caller.msg("You took {dmg} damage.".format(dmg=round(final_damage)))

            msg = "|y<COMBAT>|n {target} has failed to interrupt {attacker}'s {modifier}{attack} with {interrupt}."

            caller.msg("Note that an interrupt is both a reaction and an action. Do not attack after you pose.")
            caller.db.lf -= final_damage
            # Modify EX based on damage taken.
            # Modify the character's EX based on the damage inflicted.
            new_ex = ex_gain_on_defense(final_damage, caller.db.ex, caller.db.maxex)
            caller.db.ex = new_ex
            # Modify the attacker's EX based on the damage inflicted.
            new_attacker_ex = ex_gain_on_attack(final_damage, attacker.db.ex, attacker.db.maxex)
            attacker.db.ex = new_attacker_ex
        else:
            # Modify damage of outgoing interrupt based on relevant attack stat.
            modified_int_damage = modify_damage(outgoing_interrupt, caller)
            final_outgoing_damage = damage_calc(modified_int_damage, outgoing_interrupt_stat, outgoing_interrupt.base_stat, attacker.db.parry, attacker.db.barrier)
            # Determine how much damage the incoming attack would do if unmitigated.
            unmitigated_incoming_damage = damage_calc(incoming_damage, incoming_attack_stat, incoming_attack.base_stat, caller.db.parry, caller.db.barrier)
            # Determine how the Damage of the outgoing interrupt mitigates incoming Damage.
            mitigated_damage = interrupt_mitigation_calc(unmitigated_incoming_damage, final_outgoing_damage)
            caller.msg("You interrupt {attack} with {interrupt}.".format(attack=incoming_attack.name, interrupt=outgoing_interrupt.name))
            caller.msg("You took {dmg} damage.".format(dmg=round(mitigated_damage)))
            msg = "|y<COMBAT>|n {target} interrupts {attacker}'s {modifier}{attack} with {interrupt}."
            caller.msg("Note that an interrupt is both a reaction and an action. Do not attack after you pose.")
            caller.db.lf -= mitigated_damage
            attacker.db.lf -= final_outgoing_damage
            attacker.msg("You took {dmg} damage.".format(dmg=round(final_outgoing_damage)))
            attacker = final_action_check(attacker)
            # Modify EX based on damage taken.
            # Modify the character's EX based on the damage dealt AND inflicted.
            new_ex_first = ex_gain_on_defense(mitigated_damage, caller.db.ex, caller.db.maxex)
            caller.db.ex = new_ex_first
            new_ex_second = ex_gain_on_attack(final_outgoing_damage, caller.db.ex, caller.db.maxex)
            caller.db.ex = new_ex_second
            # Modify the attacker's EX based on the damage dealt AND inflicted.
            new_attacker_ex_first = ex_gain_on_attack(mitigated_damage, attacker.db.ex, attacker.db.maxex)
            attacker.db.ex = new_attacker_ex_first
            new_attacker_ex_second = ex_gain_on_defense(final_outgoing_damage, attacker.db.ex, attacker.db.maxex)
            attacker.db.ex = new_attacker_ex_second

        combat_string = msg.format(target=caller.key, attacker=attacker.key, modifier=modifier,
                                        attack=incoming_attack.name, interrupt=outgoing_interrupt.name)
        caller.location.msg_contents(combat_string)
        combat_log_entry(caller, combat_string)
        # If interrupting puts you at 0 LF or below, instead of the usual final action/KO check, combine them.
        if caller.db.lf <= 0:
            caller.db.KOed = True
            caller.msg("You have taken your final action and can no longer fight.")
            combat_string = "|y<COMBAT>|n {0} can no longer fight.".format(caller.name)
            caller.location.msg_contents(combat_string)
            combat_log_entry(caller, combat_string)
        # If the defender survives the interrupt, do a combat tick to clear status, as with +attack and +pass.
        else:
            combat_tick(caller)
        del caller.db.queue[id_list.index(int(incoming_attack_arg))]


class CmdArts(default_cmds.MuxCommand):
    """
        List your character's Arts.

        Usage:
          +arts

    """

    key = "+arts"
    aliases = ["arts"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        arts = caller.db.arts
        if arts is None:
            return caller.msg("Your character has no Arts. Use +setart to create some.")

        client_width = self.client_width()
        arts_table = setup_table(client_width)
        populate_table(arts_table, arts)

        arts_left_spacing = " " * ((floor(client_width / 2.0) - floor(len("Arts") / 2.0)) - 2)  # -2 for the \/
        arts_right_spacing = " " * ((floor(client_width / 2.0) - ceil(len("Arts") / 2.0)) - 2)  # -2 for the \/
        header_top = "/\\" + (client_width - 4) * "_" + "/\\" + "\n"
        arts_header = header_top + "\\/" + arts_left_spacing + "Arts" + arts_right_spacing + "\\/" + "\n"
        caller.msg(arts_header + arts_table.__str__())


class CmdListAttacks(default_cmds.MuxCommand):
    """
        List all attacks available to your character,
        including Arts and Normals.

        Usage:
          +attacks

    """

    key = "+attacks"
    aliases = ["attacks"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        arts = caller.db.arts
        if args:
            return caller.msg("The command +attacks should be input without arguments.")

        client_width = self.client_width()
        arts_table = setup_table(client_width)
        normals_table = setup_table(client_width)
        populate_table(arts_table, arts)
        populate_table(normals_table, NORMALS)

        arts_left_spacing = " " * ((floor(client_width / 2.0) - floor(len("Arts") / 2.0)) - 2)  # -2 for the \/
        arts_right_spacing = " " * ((floor(client_width / 2.0) - ceil(len("Arts") / 2.0)) - 2)  # -2 for the \/
        normals_left_spacing = " " * ((floor(client_width / 2.0) - floor(len("Normals") / 2.0)) - 2)  # -2 for the \/
        normals_right_spacing = " " * ((floor(client_width / 2.0) - ceil(len("Normals") / 2.0)) - 2)  # -2 for the \/
        header_top = "/\\" + (client_width - 4) * "_" + "/\\" + "\n"
        arts_header = header_top + "\\/" + arts_left_spacing + "Arts" + arts_right_spacing + "\\/" + "\n"
        normals_header = header_top + "\\/" + normals_left_spacing + "Normals" + normals_right_spacing + "\\/" + "\n"

        caller.msg(arts_header + arts_table.__str__())
        caller.msg(normals_header + normals_table.__str__())


class CmdCheck(default_cmds.MuxCommand):
    """
        Perform a status check. When typing "check" alone,
        display your queue (see "help queue") and any persistent
        effects on your character.

        When typing check and then an ID in your queue, e.g.,
        "check 1", list all attacks available to your character
        (Arts and Normals) and their chance to interrupt
        the incoming attack.

        Usage:
          +check
          +check <id>

    """

    key = "+check"
    aliases = ["check"]
    locks = "cmd:all()"

    def func(self):
        client_width = self.client_width()
        caller = self.caller
        args = self.args
        arts = caller.db.arts

        # Check if the command is check by itself or check with args.
        if not args:
            caller = self.caller
            display_queue(caller)
            display_status_effects(caller)
        else:
            # Confirm that the argument is just an integer (the incoming attack ID).
            if not args.isnumeric():
                return caller.msg("Please use an integer with the check command, e.g., \"check 1\".")

            attack_id = int(args)
            id_list = [attack.id for attack in caller.db.queue]

            # Now, beautifully display the arts and normals with an added column for relative interrupt chance.
            normals_left_spacing = " " * ((floor(client_width / 2.0) - floor(len("Normals") / 2.0)) - 2)  # -2 for the \/
            normals_right_spacing = " " * ((floor(client_width / 2.0) - ceil(len("Normals") / 2.0)) - 2)  # -2 for the \/
            arts_left_spacing = " " * ((floor(client_width / 2.0) - floor(len("Arts") / 2.0)) - 2)  # -2 for the \/
            arts_right_spacing = " " * ((floor(client_width / 2.0) - ceil(len("Arts") / 2.0)) - 2)  # -2 for the \/
            header_top = "/\\" + (client_width - 4) * "_" + "/\\" + "\n"
            normals_header = header_top + "\\/" + normals_left_spacing + "Normals" + normals_right_spacing + "\\/" + "\n"
            arts_header = header_top + "\\/" + arts_left_spacing + "Arts" + arts_right_spacing + "\\/" + "\n"

            normals_table = setup_table(client_width, is_check=True)
            arts_table = setup_table(client_width, is_check=True)

            for normal in NORMALS:
                # this code block is copied from CmdInterrupt
                # TODO: refactor CmdInterrupt and figure out how to move this all into a separate function
                incoming_action = caller.db.queue[id_list.index(attack_id)]
                incoming_attack = incoming_action.attack
                incoming_accuracy = incoming_attack.acc
                outgoing_accuracy = normal.acc
                bait_boole = False
                rush_boole = False
                incoming_priority_boole = False
                outgoing_priority_boole = False
                # Checking if the attacker's attack has the Priority effect.
                if hasattr(incoming_attack, "has_priority"):
                    if incoming_attack.has_priority:
                        incoming_priority_boole = True
                # Checking if the defender's previous attack had the Bait or Rush effect.
                if caller.db.is_baiting:
                    bait_boole = True
                if caller.db.is_rushing:
                    rush_boole = True
                # Checking if the defender's interrupt has the Priority effect.
                if hasattr(normal, "has_priority"):
                    if normal.has_priority:
                        outgoing_priority_boole = True
                modified_acc = interrupt_chance_calc(incoming_accuracy, outgoing_accuracy, bait_boole, rush_boole,
                                                     incoming_priority_boole, outgoing_priority_boole)

                stat_string = normal.base_stat
                if stat_string == "Power":
                    stat_string = "PWR"
                else:
                    stat_string = "KNW"

                normals_table.add_row(normal.name,
                                      "|g" + str(normal.ap_change) + "|n",
                                      normal.dmg,
                                      normal.acc,
                                      stat_string,
                                      " ",
                                      modified_acc)

            caller.msg(normals_header + normals_table.__str__())

            # If the character has arts, list them.
            if arts:
                for art in arts:
                    # art = check_for_effects(art)
                    # this code block is copied from CmdInterrupt
                    incoming_action = caller.db.queue[id_list.index(attack_id)]
                    incoming_attack = incoming_action.attack
                    incoming_accuracy = incoming_attack.acc
                    outgoing_accuracy = art.acc
                    bait_boole = False
                    rush_boole = False
                    incoming_priority_boole = False
                    outgoing_priority_boole = False
                    # Checking if the attacker's attack has the Priority effect.
                    if hasattr(incoming_attack, "has_priority"):
                        if incoming_attack.has_priority:
                            incoming_priority_boole = True
                    # Checking if the defender's previous attack had the Bait or Rush effect.
                    if caller.db.is_baiting:
                        bait_boole = True
                    if caller.db.is_rushing:
                        rush_boole = True
                    # Checking if the defender's interrupt has the Priority effect.
                    if hasattr(art, "has_priority"):
                        if art.has_priority:
                            outgoing_priority_boole = True
                    modified_acc = interrupt_chance_calc(incoming_accuracy, outgoing_accuracy, bait_boole, rush_boole,
                                                         incoming_priority_boole, outgoing_priority_boole)

                    stat_string = art.base_stat
                    if stat_string == "Power":
                        stat_string = "PWR"
                    else:
                        stat_string = "KNW"

                    arts_table.add_row(art.name,
                                      "|g" + str(art.ap_change) + "|n",
                                      art.dmg,
                                      art.acc,
                                      stat_string,
                                      effects_abbreviator(art.effects),
                                      modified_acc)

                caller.msg(arts_header + arts_table.__str__())


class CmdAim(default_cmds.MuxCommand):
    """
        Apply/remove aim effect to your next attack.

        Usage:
          +aim

    """

    key = "+aim"
    aliases = ["aim"]
    locks = "cmd:all()"

    # Note: you can never be aiming and feinting at the same time. There's no explicit check that guarantees this,
    # but the logic should make it impossible to get into that state
    def func(self):
        caller = self.caller
        if caller.db.queue:
            return caller.msg("Your queue must be empty before you Aim or Feint.")
        if caller.db.is_aiming:
            caller.db.is_aiming = False
            caller.msg("You are no longer aiming.")
        else:
            if caller.db.is_feinting:
                caller.db.is_feinting = False
                caller.msg("You are no longer feinting.")
            caller.db.is_aiming = True
            caller.msg("You have begun aiming.")


class CmdFeint(default_cmds.MuxCommand):
    """
        Apply/remove feint effect to your next attack.

        Usage:
          +feint

    """

    key = "+feint"
    aliases = ["feint"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        if caller.db.queue:
            return caller.msg("Your queue must be empty before you Aim or Feint.")
        if caller.db.is_feinting:
            caller.db.is_feinting = False
            caller.msg("You are no longer feinting.")
        else:
            if caller.db.is_aiming:
                caller.db.is_aiming = False
                caller.msg("You are no longer aiming.")
            caller.db.is_feinting = True
            caller.msg("You have begun feinting.")


class CmdRestore(default_cmds.MuxCommand):
    """
        Sets your LF to 1000, your AP to 50, and your EX to 0,
        and normalizes your status (e.g., sets block penalty to 0).

        Usage:
          +restore

    """

    key = "+restore"
    aliases = ["restore"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        # Set LF to maximum.
        caller.db.lf = caller.db.maxlf
        # Set AP to 50.
        caller.db.ap = 50
        # Set EX to 0.
        caller.db.ex = 0
        # Run the normalize_status function.
        normalize_status(caller)
        caller.msg("Your LF, AP, EX, and status effects have been reset.")


class CmdPass(default_cmds.MuxCommand):
    """
        In combat, passes your turn instead of attacking.
        This will not recover LF or AP but will, e.g., reduce block penalty
        as though your character had attacked.

        Usage:
          +pass

    """

    key = "+pass"
    aliases = ["pass"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        # First, check that the character acting is not KOed
        if caller.db.KOed:
            return caller.msg("Your character is KOed and cannot act!")
        combat_tick(caller)
        combat_string = "|y<COMBAT>|n {0} takes no action.".format(caller.name)
        caller.location.msg_contents(combat_string)
        combat_log_entry(caller, combat_string)
        # If this was the attacker's final action, they are now KOed.
        if caller.db.final_action:
            caller.db.final_action = False
            caller.db.KOed = True
            caller.msg("You have taken your final action and can no longer fight.")
            combat_string = "|y<COMBAT>|n {0} can no longer fight.".format(caller.name)
            caller.location.msg_contents(combat_string)
            combat_log_entry(caller, combat_string)