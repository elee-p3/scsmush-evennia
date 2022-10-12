from world.combat.normals import NORMALS
from evennia import default_cmds
from world.utilities.utilities import location_character_search
import random
from world.combat.combat_math import *
from world.combat.effects import AimOrFeint

def append_to_queue(caller, target, attack, attack_damage, modified_accuracy, attacker, aim_or_feint):
    # Find the actual attack object using the input attack string
    # TODO: the caller isn't used yet, but in the future we might modify attacks by the current character's equipment/stats
    attack_object = None
    for normal in NORMALS:
        if attack == normal:
            attack_object = normal
            break
    if caller.db.arts:
        for art in caller.db.arts:
            if attack == art:
                attack_object = art
                break

    # append a tuple per attack: (id, attack)
    # theoretically, you should always resolve all attacks in your queue before having more people attack you
    # this code should always just tack on at the end of the list even if that doesn't happen
    if not target.db.queue:
        last_id = 0
    else:
        last_id = max((attack["id"] for attack in target.db.queue))
    target.db.queue.append({"id":last_id+1, "attack":attack_object, "modified_damage":attack_damage, "modified_accuracy":
        modified_accuracy, "attacker":attacker, "aim_or_feint":aim_or_feint})

class CmdAttack(default_cmds.MuxCommand):
    """
        Attack! Kill! Destroy!!!

        Usage:
          +attack

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
        split_args = args.split('=')
        target = split_args[0].lower() # make everything case-insensitive
        action = split_args[1].lower()

        # caller.msg(target)
        # caller.msg(action)

        # First, check that the character attacking is not KOed
        if caller.db.KOed:
            return caller.msg("Your character is KOed and cannot act!")

        # Then check that the target is a character in the room using utility
        characters_in_room = location_character_search(location)
        # Check aliases of characters in room as well
        alias_list_in_room = [(character, character.aliases.all()) for character in characters_in_room]
        target_alias_list = [idx for idx, alias_tuple in enumerate(alias_list_in_room) if target.lower() in alias_tuple[1]]

        target_object = None
        if target_alias_list:
            target_alias_idx = target_alias_list[0]
            target_object = alias_list_in_room[target_alias_idx][0]

        # caller.msg(characters_in_room)
        if target not in [character.name.lower() for character in characters_in_room]:
            if not target_object:
                return caller.msg("Your target is not a character in this room.")

        # Find the actual character object using the input string
        for obj in location.contents:
            if not target_object:
                if target in obj.db_key.lower():
                    target_object = obj

        # Now check that the action is an attack.
        action_clean = ""
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

        # Modify the attack damage based on the relevant stat.
        modified_damage = 0
        modified_damage += action_clean.dmg
        if action_clean.base_stat == "Power":
            modified_damage += caller.db.power
        if action_clean.base_stat == "Knowledge":
            modified_damage += caller.db.knowledge

        # Modify the attack accuracy if it is the attacker's final action.
        modified_accuracy = 0
        modified_accuracy += action_clean.acc
        modified_accuracy += final_action_penalty(caller)
        # Also modify the attack accuracy if the attacker has an endure bonus from their reaction.
        if caller.db.endure_bonus:
            modified_accuracy += caller.db.endure_bonus
        # Modify the attack accuracy if the attack has the Rush effect. Apply_attacker_effects will apply is_rushing.
        if "Rush" in action_clean.effects:
            modified_accuracy += 7

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
        caller = apply_attacker_effects(caller, action_clean)

        # Append the attack to the target's queue and announce the attack.
        if caller.db.is_aiming:
            append_to_queue(caller, target_object, action_clean, modified_damage, modified_accuracy, caller, AimOrFeint.AIM)
        elif caller.db.is_feinting:
            append_to_queue(caller, target_object, action_clean, modified_damage, modified_accuracy, caller, AimOrFeint.FEINT)
        else:
            append_to_queue(caller, target_object, action_clean, modified_damage, modified_accuracy, caller, AimOrFeint.NEUTRAL)

        caller.msg("You attacked {target} with {action}.".format(target=target_object, action=action_clean))
        caller.location.msg_contents("|y<COMBAT>|n {attacker} has attacked {target} with {action}.".format(
            attacker=caller.key, target=target_object, action=action_clean))

        caller.db.is_aiming = False
        caller.db.is_feinting = False
        # If this was the attacker's final action, they are now KOed.
        if caller.db.final_action:
            caller.db.final_action = False
            caller.db.KOed = True
            caller.msg("You have taken your final action and can no longer fight.")
            caller.location.msg_contents("|y<COMBAT>|n {0} can no longer fight.".format(caller.name))

class CmdQueue(default_cmds.MuxCommand):
    """
        Oh God!! Mad Dog!!!!!

        Usage:
          +queue

    """

    key = "+queue"
    aliases = ["queue"]
    locks = "cmd:all()"

    # The queue command prints the attacks that you have been targeted with.
    # You are not allowed to attack until you've dealt with your queue.
    # Reaction commands remove attacks from your queue and resolve them.
    # Eventually, this command will assign IDs to attacks and print chances of dodging, etc.
    # For now, this just prints what you're allowed to react to.

    def func(self):
        # 1. Medium Attack -- Power -- D: 50%
        # 2. Heavy Art -- Knowledge -- D: 65%
        caller = self.caller
        if not caller.db.queue:
            caller.msg("Nothing in queue")
        else:
            for atk_obj in caller.db.queue:
                attack = atk_obj["attack"]
                id = atk_obj["id"]
                accuracy = atk_obj["modified_accuracy"]
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
                # Checking for relevant effects on the attack.
                attack = check_for_effects(attack)
                if hasattr(attack, "has_crush"):
                    if attack.has_crush:
                        crush_boole = True
                if hasattr(attack, "has_sweep"):
                    if attack.has_sweep:
                        sweep_boole = True
                # Checking for block penalty.
                block_penalty = caller.db.block_penalty
                modified_acc_for_dodge = dodge_calc(accuracy, caller.db.speed, sweep_boole, weave_boole, rush_boole)
                dodge_pct = 100 - modified_acc_for_dodge
                modified_acc_for_block = block_chance_calc(accuracy, attack.base_stat, caller.db.speed,
                                                           caller.db.parry, caller.db.barrier, crush_boole, brace_boole,
                                                           block_penalty, rush_boole)
                block_pct = 100 - modified_acc_for_block
                modified_acc_for_endure = endure_chance_calc(accuracy, attack.base_stat, caller.db.speed, caller.db.parry,
                                                             caller.db.barrier, brace_boole, rush_boole)
                endure_pct = 100 - modified_acc_for_endure
                caller.msg("{0}. {1} -- {2} -- D: {3}% B: {4}% E: {5}%".format(id, attack.name, attack.base_stat,
                                                                               dodge_pct, block_pct, endure_pct))


class CmdDodge(default_cmds.MuxCommand):
    """
        Avoid Mad Dog. Though you cannot.

        Usage:
          +dodge <queue id>

    """

    key = "+dodge"
    aliases = ["dodge"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        id_list = [attack["id"] for attack in caller.db.queue]

        # Syntax is just "dodge <id>".
        if not args.isdigit():
            return caller.msg("Please input the attack ID as an integer.")

        input_id = int(args)

        if input_id not in id_list:
            return caller.msg("Cannot find that attack in your queue.")

        # The attack is an Attack object in the queue. Roll the die and remove the attack from the queue.
        action = caller.db.queue[id_list.index(input_id)]
        attack = action["attack"]
        attack_damage = action["modified_damage"]
        accuracy = action["modified_accuracy"]
        attacker = action["attacker"]
        aim_or_feint = action["aim_or_feint"]
        random100 = random.randint(1, 100)
        sweep_boole = False
        weave_boole = False
        rush_boole = False
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

        caller.msg(aim_or_feint)
        # do the aiming/feinting modification here since we don't want to show the modified value in the queue
        if aim_or_feint == AimOrFeint.AIM:
            modified_acc += 15
        elif aim_or_feint == AimOrFeint.FEINT:
            modified_acc -= 15


        msg = ""
        is_glancing_blow = False
        if modified_acc > random100:
            # Since the attack has hit, check for glancing blow.
            attack_with_effects = check_for_effects(attack)
            sweep_boolean = hasattr(attack_with_effects, "has_sweep")
            is_glancing_blow = glancing_blow_calc(random100, modified_acc, sweep_boolean)
            if is_glancing_blow:
                # For now, halving the damage of glancing blows.
                final_damage = damage_calc(attack_damage, attack.base_stat, caller.db.parry, caller.db.barrier) / 2
                caller.msg("You have been glanced by {attack}! Mad... Mad Dog?".format(attack=attack.name))
                caller.msg("You took {dmg} damage.".format(dmg=final_damage))
            else:
                final_damage = damage_calc(attack_damage, attack.base_stat, caller.db.parry, caller.db.barrier)
                caller.msg("You have been hit by {attack}! Oh, God! Mad Dog!!!!!".format(attack=attack.name))
                caller.msg("You took {dmg} damage.".format(dmg=final_damage))

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
            caller.msg("You have successfully dodged. Good for you.")
            msg = "|y<COMBAT>|n {target} has dodged {attacker}'s {modifier}{attack}."

        if aim_or_feint == AimOrFeint.AIM:
            self.caller.location.msg_contents(msg.format(target=caller.key,
                                                         attacker=attacker.key,
                                                         modifier="Aimed ",
                                                         attack=attack.name))
        elif aim_or_feint == AimOrFeint.FEINT:
            self.caller.location.msg_contents(msg.format(target=caller.key,
                                                         attacker=attacker.key,
                                                         modifier="Feinting ",
                                                         attack=attack.name))
        else:
            self.caller.location.msg_contents(msg.format(target=caller.key,
                                                         attacker=attacker.key,
                                                         modifier="",
                                                         attack=attack.name))
        # To avoid overcomplicating the above messaging code, I'm adding the "glancing blow"
        # location message as an additional separate string.
        if is_glancing_blow:
            self.caller.location.msg_contents("|y<COMBAT>|n ** Glancing Blow **")
        # Checking after the combat location messages if the attack has put the defender at 0 LF or below.
        caller = final_action_check(caller)
        del caller.db.queue[id_list.index(input_id)]

class CmdBlock(default_cmds.MuxCommand):
    """
        Block Mad Dog. If you dare.

        Usage:
          +block <queue id>

    """

    key = "+block"
    aliases = ["block"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        id_list = [attack["id"] for attack in caller.db.queue]

        # Syntax is just "dodge <id>".
        if not args.isdigit():
            return caller.msg("Please input the attack ID as an integer.")

        input_id = int(args)

        if input_id not in id_list:
            return caller.msg("Cannot find that attack in your queue.")

        # The attack is a string in the queue. Roll the die and remove the attack from the queue.
        action = caller.db.queue[id_list.index(input_id)]
        attack = action["attack"]
        attack_damage = action["modified_damage"]
        accuracy = action["modified_accuracy"]
        attacker = action["attacker"]
        aim_or_feint = action["aim_or_feint"]
        random100 = random.randint(1, 100)
        crush_boole = False
        brace_boole = False
        rush_boole = False
        attack_with_effects = check_for_effects(attack)
        if hasattr(attack_with_effects, "has_crush"):
            if attack_with_effects.has_crush:
                crush_boole = True
        if caller.db.is_bracing:
            brace_boole = True
        if caller.db.is_rushing:
            rush_boole = True
        # Checking for block penalty.
        block_penalty = caller.db.block_penalty
        modified_acc = block_chance_calc(accuracy, attack.base_stat, caller.db.speed, caller.db.parry,
                                         caller.db.barrier, crush_boole, brace_boole, block_penalty, rush_boole)
        modified_damage = damage_calc(attack_damage, attack.base_stat, caller.db.parry, caller.db.barrier)
        # caller.msg("Base damage is: " + str(attack.dmg))
        # caller.msg("Modified damage is: " + str(modified_damage))

        # do the aiming/feinting modification here since we don't want to show the modified value in the queue
        if aim_or_feint == AimOrFeint.AIM:
            modified_acc += 15
        elif aim_or_feint == AimOrFeint.FEINT:
            modified_acc -= 15

        msg = ""

        if modified_acc > random100:
            caller.msg("You have been hit by {attack}! Oh, God! Mad Dog!!!!!".format(attack=attack.name))
            caller.msg("You took {dmg} damage.".format(dmg=modified_damage))
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
            final_damage = block_damage_calc(modified_damage)
            caller.msg("You have successfully blocked. Good for you.")
            caller.msg("You took {dmg} damage.".format(dmg=final_damage))
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
        if aim_or_feint == AimOrFeint.AIM:
            self.caller.location.msg_contents(msg.format(target=caller.key,
                                                         attacker=attacker.key,
                                                         modifier="Aimed ",
                                                         attack=attack.name))
        elif aim_or_feint == AimOrFeint.FEINT:
            self.caller.location.msg_contents(msg.format(target=caller.key,
                                                         attacker=attacker.key,
                                                         modifier="Feinting ",
                                                         attack=attack.name))
        else:
            self.caller.location.msg_contents(msg.format(target=caller.key,
                                                         attacker=attacker.key,
                                                         modifier="",
                                                         attack=attack.name))
        # Checking after the combat location message if the attack has put the defender at 0 LF or below.
        caller = final_action_check(caller)
        del caller.db.queue[id_list.index(input_id)]


class CmdEndure(default_cmds.MuxCommand):
    """
            Endure Mad Dog. Only one madder than he would try.

            Usage:
              +endure <queue id>

        """

    key = "+endure"
    aliases = ["endure"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        id_list = [attack["id"] for attack in caller.db.queue]

        # Syntax is just "endure <id>".
        if not args.isdigit():
            return caller.msg("Please input the attack ID as an integer.")

        input_id = int(args)

        if input_id not in id_list:
            return caller.msg("Cannot find that attack in your queue.")

        # The attack is an Attack object in the queue. Roll the die and remove the attack from the queue.
        action = caller.db.queue[id_list.index(input_id)]
        attack = action["attack"]
        attack_damage = action["modified_damage"]
        accuracy = action["modified_accuracy"]
        attacker = action["attacker"]
        aim_or_feint = action["aim_or_feint"]
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
        if modified_acc > random100:
            # attack_with_effects = check_for_effects(attack)
            final_damage = damage_calc(attack_damage, attack.base_stat, caller.db.parry, caller.db.barrier)
            caller.msg("You have been hit by {attack}! Oh, God! Mad Dog!!!!!".format(attack=attack.name))
            caller.msg("You took {dmg} damage.".format(dmg=final_damage))

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
            final_damage = damage_calc(attack_damage, attack.base_stat, caller.db.parry, caller.db.barrier)
            caller.msg("You endure {attack}. Mad Dog is shocked at your tenacity!!!!!".format(attack=attack.name))
            caller.msg("You took {dmg} damage.".format(dmg=final_damage))
            msg = "|y<COMBAT>|n {target} endures {attacker}'s {modifier}{attack}."
            # Now calculate endure bonus. Currently, let's set it so if you endure multiple attacks in a round,
            # you get to keep whatever endure bonus is higher. But endure bonus is not cumulative. (That's OP.)
            if endure_bonus_calc(final_damage) > caller.db.endure_bonus:
                caller.db.endure_bonus = endure_bonus_calc(final_damage)

        if aim_or_feint == AimOrFeint.AIM:
            self.caller.location.msg_contents(msg.format(target=caller.key,
                                                         attacker=attacker.key,
                                                         modifier="Aimed ",
                                                         attack=attack.name))
        elif aim_or_feint == AimOrFeint.FEINT:
            self.caller.location.msg_contents(msg.format(target=caller.key,
                                                         attacker=attacker.key,
                                                         modifier="Feinting ",
                                                         attack=attack.name))
        else:
            self.caller.location.msg_contents(msg.format(target=caller.key,
                                                         attacker=attacker.key,
                                                         modifier="",
                                                         attack=attack.name))
        # Checking after the combat location messages if the attack has put the defender at 0 LF or below.
        caller = final_action_check(caller)
        del caller.db.queue[id_list.index(input_id)]


class CmdInterrupt(default_cmds.MuxCommand):
    """
            Interrupt Mad Dog. But what can interrupt madness?

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
        id_list = [attack["id"] for attack in caller.db.queue]
        # Like +attack, +interrupt requires two arguments: a incoming attack and an outgoing interrupt.
        if "=" not in args:
            return caller.msg("Please use proper syntax: interrupt <id>=<name of interrupt>.")
        split_args = args.split("=")
        incoming_attack_arg = split_args[0]
        outgoing_interrupt_arg = split_args[1].lower()
        caller.msg(outgoing_interrupt_arg)

        # Syntax of the first argument is "interrupt <id>".
        if not incoming_attack_arg.isdigit():
            return caller.msg("Please input the attack ID as an integer.")

        if int(incoming_attack_arg) not in id_list:
            return caller.msg("Cannot find that attack in your queue.")

        # Make sure that the outgoing interrupt is an available Art/Normal.
        interrupt_clean = ""
        if outgoing_interrupt_arg not in NORMALS:
            if outgoing_interrupt_arg not in arts:
                return caller.msg("Your selected interrupt action cannot be found.")
        if outgoing_interrupt_arg in NORMALS:
            interrupt_clean = NORMALS[NORMALS.index(outgoing_interrupt_arg)]  # found action with correct capitalization
            caller.msg(NORMALS.index(outgoing_interrupt_arg))
        else:
            interrupt_clean = arts[arts.index(outgoing_interrupt_arg)]
            caller.msg(arts.index(outgoing_interrupt_arg))
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
        incoming_attack = incoming_action["attack"]
        incoming_damage = incoming_action["modified_damage"]
        incoming_accuracy = incoming_action["modified_accuracy"]
        attacker = incoming_action["attacker"]
        aim_or_feint = incoming_action["aim_or_feint"]
        outgoing_interrupt = interrupt_clean
        outgoing_damage = interrupt_clean.dmg
        outgoing_accuracy = interrupt_clean.acc
        random100 = random.randint(1, 100)
        bait_boole = False
        rush_boole = False
        incoming_priority_boole = False
        outgoing_priority_boole = False
        # Checking if the attacker's attack has the Priority effect.
        if hasattr(incoming_attack, "has_priority"):
            if incoming_attack.has_priority:
                incoming_priority_boole = True
        # Checking if the defender's previous attack had the Bait or Rush effect.
        if caller.db.is_bracing:
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
            final_damage = damage_calc(incoming_damage, incoming_attack.base_stat, caller.db.parry, caller.db.barrier)
            caller.msg("You have failed to interrupt {attack}! Oh, God! Mad Dog!!!!!".format(attack=incoming_attack.name))
            caller.msg("You took {dmg} damage.".format(dmg=final_damage))

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
            modified_int_damage = 0
            modified_int_damage += outgoing_damage
            if interrupt_clean.base_stat == "Power":
                modified_int_damage += caller.db.power
            if interrupt_clean.base_stat == "Knowledge":
                modified_int_damage += caller.db.knowledge
            # If the interrupt succeeds, halve incoming damage for now.
            final_incoming_damage = damage_calc(incoming_damage, incoming_attack.base_stat, caller.db.parry, caller.db.barrier) / 2
            final_outgoing_damage = damage_calc(modified_int_damage, outgoing_interrupt.base_stat, attacker.db.parry, attacker.db.barrier)
            caller.msg("You interrupt {attack} with {interrupt}.".format(attack=incoming_attack.name, interrupt=outgoing_interrupt.name))
            caller.msg("You took {dmg} damage.".format(dmg=final_incoming_damage))
            msg = "|y<COMBAT>|n {target} interrupts {attacker}'s {modifier}{attack} with {interrupt}."
            caller.msg("Note that an interrupt is both a reaction and an action. Do not attack after you pose.")
            caller.db.lf -= final_incoming_damage
            attacker.db.lf -= final_outgoing_damage
            attacker.msg("You took {dmg} damage.".format(dmg=final_outgoing_damage))
            # Modify EX based on damage taken.
            # Modify the character's EX based on the damage dealt AND inflicted.
            new_ex_first = ex_gain_on_defense(final_incoming_damage, caller.db.ex, caller.db.maxex)
            caller.db.ex = new_ex_first
            new_ex_second = ex_gain_on_attack(final_outgoing_damage, caller.db.ex, caller.db.maxex)
            caller.db.ex = new_ex_second
            # Modify the attacker's EX based on the damage dealt AND inflicted.
            new_attacker_ex_first = ex_gain_on_attack(final_incoming_damage, attacker.db.ex, attacker.db.maxex)
            attacker.db.ex = new_attacker_ex_first
            new_attacker_ex_second = ex_gain_on_defense(final_outgoing_damage, attacker.db.ex, attacker.db.maxex)
            attacker.db.ex = new_attacker_ex_second

        if aim_or_feint == AimOrFeint.AIM:
            self.caller.location.msg_contents(msg.format(target=caller.key,
                                                         attacker=attacker.key,
                                                         modifier="Aimed ",
                                                         attack=incoming_attack.name,
                                                         interrupt=outgoing_interrupt.name))
        elif aim_or_feint == AimOrFeint.FEINT:
            self.caller.location.msg_contents(msg.format(target=caller.key,
                                                         attacker=attacker.key,
                                                         modifier="Feinting ",
                                                         attack=incoming_attack.name,
                                                         interrupt=outgoing_interrupt.name))
        else:
            self.caller.location.msg_contents(msg.format(target=caller.key,
                                                         attacker=attacker.key,
                                                         modifier="",
                                                         attack=incoming_attack.name,
                                                         interrupt=outgoing_interrupt.name))
        # If interrupting puts you at 0 LF or below, instead of the usual final action/KO check, combine them.
        if caller.db.lf <= 0:
            caller.db.KOed = True
            caller.msg("You have taken your final action and can no longer fight.")
            caller.location.msg_contents("|y<COMBAT>|n {0} can no longer fight.".format(caller.name))
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
            return caller.msg("Your character has no Arts. Use +addart to create some.")
        for art in arts:
            name = art.name
            dmg = art.dmg
            acc = art.acc
            base_stat = art.base_stat
            effects = art.effects
            ap_change = art.ap_change
            if int(ap_change) >= 0:
                caller.msg(
                    "{0} -- AP: |g{1}|n -- Damage: {2} -- Accuracy: {3} -- {4} -- {5}".format(name, ap_change, dmg, acc,
                                                                                              base_stat,
                                                                                              effects))
            else:
                caller.msg(
                    "{0} -- AP: |c{1}|n -- Damage: {2} -- Accuracy: {3} -- {4} -- {5}".format(name, ap_change, dmg, acc,
                                                                                              base_stat,
                                                                                              effects))
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
        caller.msg("-- Normals --")
        for normal in NORMALS:
            caller.msg("{0} -- AP: |g{1}|n -- Damage: {2} -- Accuracy: {3} -- {4}".format(normal.name, normal.ap_change,
                                                                                      normal.dmg, normal.acc,
                                                                                      normal.base_stat))
        # If the character has arts, list them.
        if arts:
            caller.msg("-- Arts --")
            for art in arts:
                name = art.name
                dmg = art.dmg
                acc = art.acc
                base_stat = art.base_stat
                effects = art.effects
                ap_change = art.ap_change
                # AP costs are displayed in cyan; otherwise, the number is displayed in green.
                if int(ap_change) >= 0:
                    caller.msg(
                    "{0} -- AP: |g{1}|n -- Damage: {2} -- Accuracy: {3} -- {4} -- {5}".format(name, ap_change, dmg, acc, base_stat,
                                                                                              effects))
                else:
                    caller.msg(
                    "{0} -- AP: |c{1}|n -- Damage: {2} -- Accuracy: {3} -- {4} -- {5}".format(name, ap_change, dmg, acc, base_stat,
                                                                                              effects))


# Note: you can never be aiming and feinting at the same time. There's no explicit check that guarantees this,
# but the logic should make it impossible to get into that state
class CmdAim(default_cmds.MuxCommand):
    """
        Apply/remove aim effect to your next attack.

        Usage:
          +aim

    """

    key = "+aim"
    aliases = ["aim"]
    locks = "cmd:all()"

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
        caller.location.msg_contents("|y<COMBAT>|n {0} takes no action.".format(caller.name))
        # If this was the attacker's final action, they are now KOed.
        if caller.db.final_action:
            caller.db.final_action = False
            caller.db.KOed = True
            caller.msg("You have taken your final action and can no longer fight.")
            caller.location.msg_contents("|y<COMBAT>|n {0} can no longer fight.".format(caller.name))