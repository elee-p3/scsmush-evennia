from world.combat.normals import NORMALS
from evennia import default_cmds
from world.utilities.utilities import location_character_search
import random
from world.combat.combat_math import *
from world.combat.effects import AimOrFeint

def append_to_queue(caller, target, attack, attack_damage, attacker, aim_or_feint):
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
    target.db.queue.append({"id":last_id+1, "attack":attack_object, "modified_damage":attack_damage, "attacker":attacker, "aim_or_feint":aim_or_feint})

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

        # First, check that the character attacking has more than 0 LF
        char = self.caller.get_abilities()
        if char["lf"] <= 0:
            return caller.msg("Your character is KOed and cannot attack!")

        # Then check that the target is a character in the room using utility
        characters_in_room = location_character_search(location)
        # caller.msg(characters_in_room)
        if target not in [character.name.lower() for character in characters_in_room]:
            return caller.msg("Your target is not a character in this room.")

        # Find the actual character object using the input string
        target_object = None
        for obj in location.contents:
            if target in obj.db_key.lower():
                target_object = obj

        # Now check that the action is an attack, which for now is just normals.
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
        # I figure a queue should be a list and the ID should be the attack's index +1.
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

        # If the character has insufficient AP to use that move, cancel the attack.
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

        # Append the attack to the target's queue and announce the attack.
        attacker = caller
        if caller.db.is_aiming:
            append_to_queue(caller, target_object, action_clean, modified_damage, attacker, AimOrFeint.AIM)
        elif caller.db.is_feinting:
            append_to_queue(caller, target_object, action_clean, modified_damage, attacker, AimOrFeint.FEINT)
        else:
            append_to_queue(caller, target_object, action_clean, modified_damage, attacker, AimOrFeint.NEUTRAL)

        caller.msg("You attacked {target} with {action}.".format(target=target_object, action=action_clean))
        caller.location.msg_contents("|y<COMBAT>|n {attacker} has attacked {target} with {action}.".format(
            attacker=attacker.key, target=target_object, action=action_clean))

        caller.db.is_aiming = False
        caller.db.is_feinting = False

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
                modified_acc_for_dodge = dodge_calc(attack.acc, caller.db.speed)
                dodge_pct = 100 - modified_acc_for_dodge
                modified_acc_for_block = block_chance_calc(attack.acc, attack.base_stat, caller.db.speed, caller.db.parry, caller.db.barrier)
                block_pct = 100 - modified_acc_for_block
                caller.msg("{0}. {1} -- {2} -- D: {3}% B: {4}%".format(id, attack.name, attack.base_stat, dodge_pct, block_pct))


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
        attacker = action["attacker"]
        aim_or_feint = action["aim_or_feint"]
        random100 = random.randint(1, 100)
        modified_acc = dodge_calc(attack.acc, caller.db.speed)

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
        attacker = action["attacker"]
        aim_or_feint = action["aim_or_feint"]
        random100 = random.randint(1, 100)
        modified_acc = block_chance_calc(attack.acc, attack.base_stat, caller.db.speed, caller.db.parry, caller.db.barrier)
        modified_damage = damage_calc(attack.dmg, attack.base_stat, caller.db.parry, caller.db.barrier)
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
        else:
            final_damage = block_damage_calc(modified_damage)
            # caller.msg("Final damage is: " + str(final_damage))
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

        del caller.db.queue[id_list.index(input_id)]

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