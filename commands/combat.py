import copy
import csv
import random
from math import floor, ceil

from evennia import default_cmds
from evennia.utils import evtable
from world.arts.models import Arts
from world.combat.attacks import AttackToQueue, AttackDuringAction, ActionResult
from world.combat.combat_functions import *
from world.combat.effects import AimOrFeint
from world.combat.normals import NORMALS
from world.utilities.utilities import *
from world.utilities.tables import setup_table, populate_table



def record_combat(defender, attack_instance, reaction_name, is_success, dmg):
    attacker = find_attacker_from_key(attack_instance.attacker_key)
    attack = attack_instance.attack
    with open("combat_record.csv", "a", newline='') as combat_csv:
        csvwriter = csv.writer(combat_csv)
        csvwriter.writerow([attacker.key,
                            attacker.db.power,
                            attacker.db.knowledge,
                            defender.key,
                            defender.db.parry,
                            defender.db.barrier,
                            defender.db.speed,
                            defender.db.block_penalty,
                            defender.db.endure_bonus,
                            defender.db.final_action,
                            defender.db.is_weaving,
                            defender.db.is_bracing,
                            defender.db.is_baiting,
                            defender.db.is_rushing,
                            attack.name,
                            attack.ap,
                            attack.dmg,
                            attack.acc,
                            attack.stat,
                            str(attack.effects),
                            attack_instance.aim_or_feint,
                            reaction_name,
                            is_success,
                            dmg])

def display_queue(calling_class, caller):
    # This function is called by both the "queue" command and by "check" when input without arguments.
    if not caller.db.queue:
        caller.msg("Nothing in queue.")
    else:
        client_width = calling_class.client_width()
        queue_table = calling_class.styled_table("|wID#",
                                                 "|wAttack Name",
                                                 "|wStat",
                                                 "|wDodge%",
                                                 "|wBlock%",
                                                 "|wEndure%"
                                                 )
        for atk_obj in caller.db.queue:
            attack = atk_obj.attack
            id = atk_obj.id
            modified_acc_for_dodge = dodge_calc(caller, atk_obj)
            dodge_pct = 100 - modified_acc_for_dodge
            modified_acc_for_block = block_chance_calc(caller, atk_obj)
            block_pct = 100 - modified_acc_for_block
            modified_acc_for_endure = endure_chance_calc(caller, atk_obj)
            endure_pct = 100 - modified_acc_for_endure

            queue_table.add_row(id,
                                attack.name,
                                attack.stat,
                                round(dodge_pct),
                                round(block_pct),
                                round(endure_pct))

        caller.msg(queue_table)


class CmdSheet(default_cmds.MuxCommand):
    # TODO(RF): New command. Tied to combat commands. Add to combat.py? Also contains some finger info.
    """
    List attributes

    Usage:
      sheet, score

    Displays a list of your current ability values.
    """
    key = "sheet"
    aliases = ["score"]
    lock = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        client_width = self.client_width()
        char = caller.get_abilities()
        arts, base_arts, normals = filter_and_modify_arts(caller)
        sheetMsg = "/\\" + (client_width - 4) * "_" + "/\\" + "\n"  # top border

        header = ""
        alias_list = [x for x in self.caller.aliases.all() if " " not in x]
        # find all aliases that don't contain spaces (this was to get rid of "An Ivo" or "One Ivo")
        if alias_list:
            alias = min(alias_list, key=len).title()
            header = char["name"] + " (" + alias + ")" + " - " + char["occupation"]
        else:
            header = char["name"] + " - " + char["occupation"]

        left_spacing = " " * ((floor(client_width / 2.0) - floor(len(header) / 2.0)) - 2)  # -2 for the \/
        right_spacing = " " * ((floor(client_width / 2.0) - ceil(len(header) / 2.0)) - 2)  # -2 for the \/
        nameBorder = "\\/" + left_spacing + header + right_spacing + "\\/"
        sheetMsg += nameBorder + "\n"

        charInfoTable = evtable.EvTable(border_left_char="|", border_right_char="|", border_top_char="-",
                                        border_bottom_char=" ", width=client_width, border="table")
        charInfoTable.add_column()
        charInfoTable.add_column()
        charInfoTable.add_column()
        charInfoTable.add_column()
        charInfoTable.reformat_column(0, align='l')  # resource label
        charInfoTable.reformat_column(1, align='r')  # resource value
        charInfoTable.reformat_column(2, align='l')  # stat label
        charInfoTable.reformat_column(3, align='l')  # stat value
        charInfoTable.add_row("LF",
                              "{0}/{1}  ".format(int(char["lf"]), int(char["maxlf"])),
                              "  Power",
                              "  {0}".format(char["power"]))
        charInfoTable.add_row(self.get_colored_meter(caller.db.lf, caller.db.maxlf, client_width),
                              "",
                              "  Knowledge",
                              "  {0}".format(char["knowledge"]))
        charInfoTable.add_row("AP",
                              "{0}/{1}  ".format(int(char["ap"]), int(char["maxap"])),
                              "  Parry",
                              "  {0}".format(char["parry"]))
        charInfoTable.add_row(self.get_colored_meter(caller.db.ap, caller.db.maxap, client_width),
                              "",
                              "  Barrier",
                              "  {0}".format(char["barrier"]))
        charInfoTable.add_row("EX",
                              "{0}%/{1}%  ".format(int(char["ex"]), int(char["maxex"])),
                              "  Speed",
                              "  {0}".format(char["speed"]))
        charInfoTable.add_row(self.get_colored_meter(caller.db.ex, caller.db.maxex, client_width),
                              "",
                              "",
                              "")

        charInfoString = charInfoTable.__str__()
        sheetMsg += charInfoString[:charInfoString.rfind('\n')] + "\n"  # delete last newline (i.e. bottom border)

        # print Arts table, attached to the bottom of the character sheet
        left_spacing = floor(client_width / 2.0) - 3  # -2 for the borders
        right_spacing = ceil(client_width / 2.0) - 3  # -2 for the borders
        sheetMsg += "|" + "=" * left_spacing + "ARTS" + "=" * right_spacing + "|"

        arts_table = setup_table(client_width, is_sheet=True)
        populate_table(arts_table, arts, base_arts)
        arts_string = arts_table.__str__()
        sheetMsg += arts_string[arts_string.find('\n'):arts_string.rfind('\n')] + "\n"

        sheetMsg += "/\\" + (client_width - 4) * "_" + "/\\" + "\n"
        sheetMsg += "\\/" + (client_width - 4) * " " + "\\/" + "\n"

        self.caller.msg(sheetMsg)

    # return a colored bar for various meters (e.g. LF, AP, EX)
    def get_colored_meter(self, current_val, max_val, client_width):
        remaining_resource_ratio = current_val/max_val
        # we're drawing 10 characters (at max resources): 3 red, 4 yellow, 3 green
        # thus we round to the nearest 10th and multiply by 10 to get an integer
        max_character_count = int(round(client_width/4 - 1))
        red_count = floor(max_character_count/3)
        yellow_count = floor(max_character_count * 2/3) - red_count
        red_yellow_count = red_count + yellow_count
        resource_character_count = int(round(remaining_resource_ratio * max_character_count))

        meter = "["
        if resource_character_count > red_yellow_count:
            diff = resource_character_count - red_yellow_count
            meter += "|r{}|n|y{}|n|g{}|n{}".format('=' * red_count, '=' * yellow_count,  '=' * diff, '-' * (max_character_count - resource_character_count))
        elif resource_character_count > red_count:
            diff = resource_character_count - red_count
            meter += "|r{}|n|y{}|n{}".format('=' * red_count, '=' * diff, '-' * (max_character_count - resource_character_count))
        else:
            meter += "|r{}|n{}".format('=' * resource_character_count, '-' * (max_character_count - resource_character_count))

        return meter + "]"


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
    aliases = ["attack", "target", "heal"]
    locks = "cmd:all()"

    def func(self):
        # Attack should take two arguments: a target and an attack name
        # Format should be "attack x=y" where x is target and y is attack
        caller = self.caller
        location = caller.location
        args = self.args
        arts, base_arts, modified_normals = filter_and_modify_arts(caller)
        switches = self.switches
        # For attack/wild and heal/[debuff] (for Cure). Switches is a list of strings split by /. Send to heal_check.

        if len(args) == 0:
            return caller.msg("You need to specify a target and action. See `help attack` for syntax.")

        split_args = args.split('=')

        if len(split_args) != 2:
            return caller.msg("Unrecognized command syntax. See `help attack`.")

        target = split_args[0].lower() # make everything case-insensitive
        action = split_args[1].lower()

        aim_or_feint = AimOrFeint.NEUTRAL
        if caller.db.is_aiming:
            if caller.db.buffs["Haste"] > 0:
                aim_or_feint = AimOrFeint.HASTED_AIM
            else:
                aim_or_feint = AimOrFeint.AIM
        if caller.db.is_feinting:
            if caller.db.buffs["Blink"] > 0:
                aim_or_feint = AimOrFeint.BLINKED_FEINT
            else:
                aim_or_feint = AimOrFeint.FEINT

        # First, check that the character attacking is not KOed
        if caller.db.KOed:
            return caller.msg("Your character is KOed and cannot act.")
        if caller.db.stunned:
            return caller.msg("Your character is stunned and must 'pass' this turn.")

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
        if action in arts:
            action_clean = next(x for x in arts if x == action)
        elif action in modified_normals:
            action_clean = next(x for x in modified_normals if x == action)
        else:
            return caller.msg("Your selected action cannot be found.")

        # If the target is here and the action exists, then we add the attack to the target's queue.
        # The attack should be assigned an ID based on its place in the queue.
        # Check if the "queue" attribute exists and, if not, create an empty list first.
        if target_object.db.queue is None:
            target_object.db.queue = []

        # If the character has insufficient AP or EX to use that move, cancel the attack.
        # Otherwise, set their EX from 100 to 0.
        total_ap_change = action_clean.ap
        if caller.db.is_aiming or caller.db.is_feinting:
            if "Heal" in action_clean.effects:
                return caller.msg("You cannot Aim or Feint a healing Art.")
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

        # The attack is now confirmed. Apply any persistent effects that will affect the attacker regardless of
        # the attack's future success.
        caller = apply_attack_effects_to_attacker(caller, action_clean)

        # Modify the damage and accuracy of the attack based on our combat functions.
        # Before modifying damage, check if the action is a heal, as there the target's defense stat will not apply.
        if "Heal" in action_clean.effects:
            heal_check(action_clean, caller, target_object, switches)
        else:
            # action_clean.dmg = modify_damage(action_clean, caller)

            new_id = assign_attack_instance_id(target_object)

            # Confirm here before passing along the attack that the switch is a valid one.
            if switches:
                error_found = attack_switch_check(caller, switches)
                if error_found:
                    return caller.msg("Error: a switch on your attack was not recognized. See 'help attack'.")

            target_object.db.queue.append(AttackToQueue(new_id, action_clean, caller.key, aim_or_feint, switches))

            caller.msg("You attacked {target} with {action}.".format(target=target_object, action=action_clean))
            combat_string = "|y<COMBAT>|n {attacker} has attacked {target} with {action}.".format(
                attacker=caller.key, target=target_object, action=action_clean)
            caller.location.msg_contents(combat_string)
            # TODO: when we generalize the log_entry function, replace all combat_log_entry with that + combat parameter
            combat_log_entry(caller, combat_string)

        # "Tick" to have a round pass.
        combat_tick(caller, action_clean)
        # If this was the attacker's final action, they are now KOed.
        if caller.db.final_action:
            final_action_taken(caller)


class CmdQueue(default_cmds.MuxCommand):
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
        display_queue(self, caller)


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

        # The attack is an AttackInstance object in the queue. Roll the die and remove the attack from the queue.
        action = caller.db.queue[id_list.index(input_id)]
        attack = action.attack
        attacker = find_attacker_from_key(action.attacker_key)
        aim_or_feint = action.aim_or_feint
        modifier = action.modifier
        random100 = random.randint(1, 100)

        # modified_acc = dodge_calc(caller, action)
        dodge_pct = dodge_calc(caller, action)

        # do the aiming/feinting modification here since we don't want to show the modified value in the queue
        dodge_pct = modify_aim_and_feint(dodge_pct, "dodge", aim_or_feint)

        msg = ""
        is_glancing_blow = False
        if dodge_pct > random100:
            # Since the attack has hit, check for critical hit.
            final_damage = damage_calc(action, caller)
            is_critical_hit, final_damage = critical_hits(final_damage, action)
            # If the attack is not a critical hit, check for glancing blow (so there are no glancing crits).
            is_glancing_blow = glancing_blow_calc(random100, dodge_pct, action.has_sweep)
            if is_critical_hit:
                msg = damage_message_strings(ActionResult.REACT_CRIT_FAIL, caller, attack, final_damage)
            elif is_glancing_blow:
                # For now, halving the damage of glancing blows.
                final_damage = final_damage / 2
                msg = damage_message_strings(ActionResult.GLANCING_BLOW, caller, attack, final_damage)
            else:
                msg = damage_message_strings(ActionResult.REACT_FAIL, caller, attack, final_damage)

            caller.db.lf -= final_damage

            # Modify EX based on damage taken.
            caller.db.ex, attacker.db.ex = modify_ex_on_hit(final_damage, caller, attacker)

            # Effect check
            apply_debuff(attack, attacker, caller)
            if "Drain" in attack.effects:
                drain_check(attack, attacker, caller, final_damage)
            if "Dispel" in attack.effects:
                dispel_check(caller)
            if "Long-Range" in attack.effects and attacker.key not in caller.db.ranged_knockback[1]:
                ranged_knockback(caller, attacker)
            record_combat(caller, action, "dodge", False, final_damage)
        else:
            caller.msg("You have successfully dodged {attack}.".format(attack=attack.name))
            msg = "|y<COMBAT>|n {target} has dodged {attacker}'s {modifier}{attack}."
            record_combat(caller, action, "dodge", True, 0)

        combat_string = msg.format(target=caller.key, attacker=attacker.key, modifier=modifier, attack=attack.name)
        caller.location.msg_contents(combat_string)
        combat_log_entry(caller, combat_string)
        # Checking after the combat location messages if the attack has put the defender at 0 LF or below.
        final_action_check(caller)
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

        action = caller.db.queue[id_list.index(input_id)]
        attack = action.attack
        attacker = find_attacker_from_key(action.attacker_key)
        aim_or_feint = action.aim_or_feint
        modifier = action.modifier
        random100 = random.randint(1, 100)

        # Find the attacker's relevant attack stat for damage_calc.
        modified_acc = block_chance_calc(caller, action)
        modified_damage = damage_calc(action, caller)

        # do the aiming/feinting modification here since we don't want to show the modified value in the queue
        modified_acc = modify_aim_and_feint(modified_acc, "block", aim_or_feint)

        msg = ""

        if modified_acc > random100:
            # Since the attack has hit, check for critical hit.
            is_critical_hit, final_damage = critical_hits(modified_damage, action)
            if is_critical_hit:
                msg = damage_message_strings(ActionResult.REACT_CRIT_FAIL, caller, attack, final_damage)
            else:
                msg = damage_message_strings(ActionResult.REACT_FAIL, caller, attack, final_damage)
            caller.db.lf -= modified_damage

            # Modify EX based on the damage.
            caller.db.ex, attacker.db.ex = modify_ex_on_hit(final_damage, caller, attacker)

            # Modify the defender's block penalty (a little, since the block failed).
            block_bool = False
            new_block_penalty = accrue_block_penalty(caller, modified_damage, block_bool, action)
            caller.db.block_penalty = new_block_penalty
            # Apply debuffs only on failed blocks
            apply_debuff(attack, attacker, caller)
            if "Drain" in attack.effects:
                drain_check(attack, attacker, caller, modified_damage)
            if "Dispel" in attack.effects:
                dispel_check(caller)
            record_combat(caller, action, "block", False, modified_damage)
        else:
            final_damage = block_damage_calc(modified_damage, caller.db.block_penalty)
            msg = damage_message_strings(ActionResult.BLOCK_SUCCESS, caller, attack, final_damage)
            caller.db.lf -= final_damage

            # Modify EX (based on modified, not final, dmg).
            caller.db.ex, attacker.db.ex = modify_ex_on_hit(modified_damage, caller, attacker)

            # Modify the defender's block penalty (a lot, since the block succeeded). Based on modified, not final, dmg.
            block_bool = True
            new_block_penalty = accrue_block_penalty(caller, modified_damage, block_bool, action)
            caller.db.block_penalty = new_block_penalty
            if "Drain" in attack.effects:
                drain_check(attack, attacker, caller, final_damage)
            record_combat(caller, action, "block", True, final_damage)

        if "Long-Range" in attack.effects and attacker.key not in caller.db.ranged_knockback[1]:
            ranged_knockback(caller, attacker)
        combat_string = msg.format(target=caller.key, attacker=attacker.key, modifier=modifier, attack=attack.name)
        caller.location.msg_contents(combat_string)
        combat_log_entry(caller, combat_string)
        # Checking after the combat location message if the attack has put the defender at 0 LF or below.
        final_action_check(caller)
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
        attacker = find_attacker_from_key(action.attacker_key)
        aim_or_feint = action.aim_or_feint
        modifier = action.modifier
        random100 = random.randint(1, 100)

        modified_acc = endure_chance_calc(caller, action)

        # do the aiming/feinting modification here since we don't want to show the modified value in the queue
        modified_acc = modify_aim_and_feint(modified_acc, "endure", aim_or_feint)

        msg = ""
        attacker_stat = find_attacker_stat(attacker, attack.stat)
        final_damage = damage_calc(action, caller)
        if modified_acc > random100:
            # Since the attack has hit, check for critical hit.
            is_critical_hit, final_damage = critical_hits(final_damage, action)
            if is_critical_hit:
                msg = damage_message_strings(ActionResult.REACT_CRIT_FAIL, caller, attack, final_damage)
            else:
                msg = damage_message_strings(ActionResult.REACT_FAIL, caller, attack, final_damage)
            record_combat(caller, action, "endure", False, final_damage)
        else:
            msg = damage_message_strings(ActionResult.ENDURE_SUCCESS, caller, attack, final_damage)

            # Now calculate endure bonus. Currently, let's set it so if you endure multiple attacks in a round,
            # you get to keep whatever endure bonus is higher. But endure bonus is not cumulative. (That's OP.)
            if endure_bonus_calc(final_damage) > caller.db.endure_bonus:
                caller.db.endure_bonus = endure_bonus_calc(final_damage)
            record_combat(caller, action, "endure", True, final_damage)

        caller.db.lf -= final_damage

        # Modify EX.
        caller.db.ex, attacker.db.ex = modify_ex_on_hit(final_damage, caller, attacker)

        # Apply debuffs regardless of if endure succeeds or fails
        apply_debuff(attack, attacker, caller)
        if "Drain" in attack.effects:
            drain_check(attack, attacker, caller, final_damage)
        if "Dispel" in attack.effects:
            dispel_check(caller)
        if "Long-Range" in attack.effects and attacker.key not in caller.db.ranged_knockback[1]:
            ranged_knockback(caller, attacker)

        combat_string = msg.format(target=caller.key, attacker=attacker.key, modifier=modifier, attack=attack.name)
        caller.location.msg_contents(combat_string)
        combat_log_entry(caller, combat_string)
        # Checking after the combat location messages if the attack has put the defender at 0 LF or below.
        final_action_check(caller)
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
        switches = self.switches
        arts, base_arts, normals = filter_and_modify_arts(caller)
        id_list = [attack.id for attack in caller.db.queue]
        # Like +attack, +interrupt requires two arguments: a incoming attack and an outgoing interrupt.
        if "=" not in args:
            return caller.msg("Please use proper syntax: interrupt <id>=<name of interrupt>.")
        split_args = args.split("=")
        incoming_attack_id = split_args[0]
        outgoing_attack_name = split_args[1].lower()

        # Syntax of the first argument is "interrupt <id>".
        if not incoming_attack_id.isdigit():
            return caller.msg("Please input the attack ID as an integer.")

        if int(incoming_attack_id) not in id_list:
            return caller.msg("Cannot find that attack in your queue.")

        # Make sure that the outgoing interrupt is an available Art/Normal.
        if outgoing_attack_name not in normals:
            if outgoing_attack_name not in arts:
                return caller.msg("Your selected interrupt action cannot be found.")
        if outgoing_attack_name in normals:
            outgoing_interrupt = next(x for x in normals if x == outgoing_attack_name.lower())
        else:
            outgoing_interrupt = next(x for x in arts if x == outgoing_attack_name.lower())
        # Check if the interrupter is currently Aiming or Feinting.
        if caller.db.is_aiming:
            return caller.msg("You cannot Aim an interrupt. First type 'aim' again to cease aiming.")
        if caller.db.is_feinting:
            return caller.msg("You cannot Feint an interrupt. First type 'feint' again to cease feinting.")
        # If the character has insufficient AP or EX to use that move, cancel the interrupt.
        # Otherwise, if EX move, set their EX from 100 to 0.
        total_ap_change = outgoing_interrupt.ap
        if caller.db.ap + total_ap_change < 0:
            return caller.msg("You do not have enough AP to do that.")
        if "EX" in outgoing_interrupt.effects:
            if caller.db.ex - 100 < 0:
                return caller.msg("You do not have enough EX to do that.")
            caller.db.ex = 0
        caller.db.ap += total_ap_change

        # The attack is an Attack object in the queue. Roll the die and remove the attack from the queue.
        incoming_atk_in_queue = caller.db.queue[id_list.index(int(incoming_attack_id))]
        incoming_atk = incoming_atk_in_queue.attack
        incoming_damage = incoming_atk.dmg
        attacker = find_attacker_from_key(incoming_atk_in_queue.attacker_key)
        aim_or_feint = incoming_atk_in_queue.aim_or_feint
        modifier = incoming_atk_in_queue.modifier
        random100 = random.randint(1, 100)

        incoming_attack_stat = find_attacker_stat(attacker, incoming_atk.stat)
        outgoing_interrupt_stat = find_attacker_stat(caller, outgoing_interrupt.stat)

        # Spawn an InterruptInstance here to begin modifying its accuracy, etc. Will need this for critical_hits
        interrupt = AttackDuringAction(outgoing_interrupt, caller.key, switches)

        interrupt.attack.acc = interrupt_chance_calc(caller, incoming_atk_in_queue, outgoing_interrupt)

        # effects of aim and feint on incoming attack checked here
        interrupt.attack.acc = modify_aim_and_feint(interrupt.attack.acc, "interrupt", aim_or_feint)

        modified_acc = interrupt.attack.acc

        msg = ""
        # In case of interrupt failure
        if modified_acc < random100:
            final_damage = damage_calc(incoming_atk_in_queue, caller)

            # Check for Protect/Reflect moderate damage mitigation.
            final_damage = protect_and_reflect_check(final_damage, caller, incoming_atk, False)

            # Since the incoming attack has hit, check for critical hit.
            is_critical_hit, final_damage = critical_hits(final_damage, incoming_atk_in_queue)
            if is_critical_hit:
                msg = damage_message_strings(ActionResult.INTERRUPT_CRIT_FAIL, caller, incoming_atk, final_damage)
            else:
                msg = damage_message_strings(ActionResult.INTERRUPT_FAIL, caller, incoming_atk, final_damage)

            caller.msg("Note that an interrupt is both a reaction and an action. Do not attack after you pose.")
            caller.db.lf -= final_damage

            # Modify EX based on damage.
            caller.db.ex, attacker.db.ex = modify_ex_on_hit(final_damage, caller, attacker)

            # Apply debuffs only if interrupt fails
            apply_debuff(incoming_atk, attacker, caller)
            if "Drain" in incoming_atk.effects:
                drain_check(incoming_atk_in_queue, attacker, caller, final_damage)
            if "Dispel" in incoming_atk.effects:
                dispel_check(caller)
            if "Long-Range" in incoming_atk.effects and attacker.key not in caller.db.ranged_knockback[1]:
                ranged_knockback(caller, attacker)
            record_combat(caller, incoming_atk_in_queue, "interrupt", False, final_damage)

        # In case of interrupt success
        else:
            # Modify damage of outgoing interrupt based on relevant attack stat.
            # modified_int_damage = modify_damage(outgoing_interrupt, caller)
            final_outgoing_damage = damage_calc(interrupt, attacker)

            # Check if the interrupt is a critical hit!
            is_critical_hit, final_outgoing_damage = critical_hits(final_outgoing_damage, interrupt)

            # Determine how much damage the incoming attack would do if unmitigated.
            unmitigated_incoming_damage = damage_calc(incoming_atk_in_queue, caller)

            # Determine how the Damage of the outgoing interrupt mitigates incoming Damage.
            mitigated_damage = interrupt_mitigation_calc(unmitigated_incoming_damage, final_outgoing_damage)

            # Check for Protect/Reflect moderate damage mitigation.
            mitigated_damage = protect_and_reflect_check(mitigated_damage, caller, incoming_atk, True)

            if is_critical_hit:
                msg = damage_message_strings(ActionResult.INTERRUPT_CRIT_SUCCESS, caller, incoming_atk,
                                             final_outgoing_damage, outgoing_interrupt, mitigated_damage, attacker)
            else:
                msg = damage_message_strings(ActionResult.INTERRUPT_SUCCESS, caller, incoming_atk,
                                             final_outgoing_damage, outgoing_interrupt, mitigated_damage, attacker)
            caller.msg("Note that an interrupt is both a reaction and an action. Do not attack after you pose.")
            caller.db.lf -= mitigated_damage
            attacker.db.lf -= final_outgoing_damage

            # Check if your successful interrupt was your final action.
            final_action_check(attacker)

            # Modify EX.
            caller.db.ex, attacker.db.ex = modify_ex_on_interrupt_success(mitigated_damage, final_outgoing_damage, caller, attacker)

            # Interrupting a Drain attack partially drains you, but if you interrupt Long-Range, you're not knocked back
            if "Drain" in incoming_atk.effects:
                drain_check(incoming_atk_in_queue, attacker, caller, mitigated_damage)

            # Apply debuffs to interrupted attacker
            apply_debuff(outgoing_interrupt, caller, attacker)
            if "Drain" in outgoing_interrupt.effects:
                drain_check(outgoing_interrupt, caller, attacker, final_outgoing_damage)
            if "Dispel" in outgoing_interrupt.effects:
                dispel_check(attacker)
            if "Long-Range" in outgoing_interrupt.effects and caller.key not in attacker.db.ranged_knockback[1]:
                ranged_knockback(attacker, caller)
            record_combat(caller, incoming_atk_in_queue, "interrupt", True, mitigated_damage)

        combat_string = msg.format(target=caller.key, attacker=attacker.key, modifier=modifier,
                                   attack=incoming_atk.name, interrupt=outgoing_interrupt.name)
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
            combat_tick(caller, outgoing_interrupt)
            # Might have just taken poison damage and been reduced below 0 LF then! Check, but can't be KOed from that.
            final_action_check(caller)
        del caller.db.queue[id_list.index(int(incoming_attack_id))]


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
        arts, base_arts, modified_normals = filter_and_modify_arts(caller)
        if arts is None:
            return caller.msg("Your character has no Arts. Use +setart to create some.")

        client_width = self.client_width()
        arts_table = setup_table(client_width)
        populate_table(arts_table, arts, base_arts)

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
        arts, base_arts, modified_normals = filter_and_modify_arts(caller)
        if args:
            return caller.msg("The command +attacks should be input without arguments.")

        client_width = self.client_width()
        arts_table = setup_table(client_width)
        normals_table = setup_table(client_width)
        populate_table(arts_table, arts, base_arts)
        populate_table(normals_table, modified_normals, NORMALS)

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
        arts, base_arts, modified_normals = filter_and_modify_arts(caller)

        # Check if the command is check by itself or check with args.
        if not args:
            caller = self.caller
            display_queue(self, caller)
            display_status_effects(caller)
        else:
            # Confirm that the argument is just an integer (the incoming attack ID).
            if not args.isnumeric():
                return caller.msg("Please use an integer with the check command, e.g., \"check 1\".")

            attack_id = int(args)
            id_list = [attack.id for attack in caller.db.queue]
            interrupted_action = caller.db.queue[id_list.index(attack_id)]

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

            populate_table(normals_table, modified_normals, NORMALS, interrupted_action, caller)
            caller.msg(normals_header + normals_table.__str__())

            # If the character has arts, list them.
            if arts:
                populate_table(arts_table, arts, base_arts, interrupted_action, caller)
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
        combat_tick(caller, None)
        combat_string = "|y<COMBAT>|n {0} takes no action.".format(caller.name)
        caller.location.msg_contents(combat_string)
        combat_log_entry(caller, combat_string)
        if caller.db.stunned:
            caller.db.stunned = False
            caller.msg("Your character is no longer stunned.")
        # Clear all hexes, if applicable.
        clear_hexes(caller)
        # If this was the attacker's final action, they are now KOed.
        if caller.db.final_action:
            final_action_taken(caller)

