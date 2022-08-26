from world.combat.normals import NORMALS
from evennia import default_cmds
from world.utilities.utilities import location_character_search
import random
from world.combat.combat_math import *

def append_to_queue(caller, target, attack):
    # Find the actual attack object using the input attack string
    # TODO: it's just the normals for now, but we'll concatenate a full list of attacks once characters have their own custom attacks
    # TODO: the caller isn't used yet, but in the future we might modify attacks by the current character's equipment/stats
    attack_object = None
    for normal in NORMALS:
        if attack == normal:
            attack_object = normal
            break
    for art in caller.db.arts:
        if attack == art:
            attack_object = art


    # append a tuple per attack: (id, attack)
    # theoretically, you should always resolve all attacks in your queue before having more people attack you
    # this code should always just tack on at the end of the list even if that doesn't happen
    if not target.db.queue:
        last_id = 0
    else:
        last_id = max((attack["id"] for attack in target.db.queue))
    target.db.queue.append({"id":last_id+1, "attack":attack_object})

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
        true_damage = int(action_clean.dmg)
        if action_clean.base_stat == "Power":
            true_damage += int(caller.db.power)
        if action_clean.base_stat == "Knowledge":
            true_damage += int(caller.db.knowledge)
        action_clean.dmg = true_damage

        append_to_queue(caller, target_object, action_clean)
        caller.msg("You attacked {target} with {action}.".format(target=target_object, action=action_clean))

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

        # The attack is a string in the queue. Roll the die and remove the attack from the queue.
        attack = caller.db.queue[id_list.index(input_id)]["attack"]
        random100 = random.randint(1, 100)
        modified_acc = dodge_calc(attack.acc, caller.db.speed)
        if modified_acc > random100:
            final_damage = damage_calc(attack.dmg, attack.base_stat, caller.db.parry, caller.db.barrier)
            caller.msg("You have been hit by {attack}! Oh, God! Mad Dog!!!!!".format(attack=attack.name))
            caller.msg("You took {dmg} damage.".format(dmg=final_damage))
            caller.db.lf -= final_damage
        else:
            caller.msg("You have successfully dodged. Good for you.")

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
        attack = caller.db.queue[id_list.index(input_id)]["attack"]
        random100 = random.randint(1, 100)
        modified_acc = block_chance_calc(attack.acc, attack.base_stat, caller.db.speed, caller.db.parry, caller.db.barrier)
        modified_damage = damage_calc(attack.dmg, attack.base_stat, caller.db.parry, caller.db.barrier)
        if modified_acc > random100:
            caller.msg("You have been hit by {attack}! Oh, God! Mad Dog!!!!!".format(attack=attack.name))
            caller.msg("You took {dmg} damage.".format(dmg=modified_damage))
            caller.db.lf -= modified_damage
        else:
            final_damage = block_damage_calc(modified_damage)
            caller.msg("You have successfully blocked. Good for you.")
            caller.msg("You took {dmg} damage.".format(dmg=final_damage))
            caller.db.lf -= final_damage

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
class CmdAttacks(default_cmds.MuxCommand):
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
        if arts:
            caller.msg("-- Arts --")
            for art in arts:
                name = art.name
                dmg = art.dmg
                acc = art.acc
                base_stat = art.base_stat
                effects = art.effects
                ap_change = art.ap_change
                if int(ap_change) >= 0:
                    caller.msg(
                    "{0} -- AP: |g{1}|n -- Damage: {2} -- Accuracy: {3} -- {4} -- {5}".format(name, ap_change, dmg, acc, base_stat,
                                                                                              effects))
                else:
                    caller.msg(
                    "{0} -- AP: |c{1}|n -- Damage: {2} -- Accuracy: {3} -- {4} -- {5}".format(name, ap_change, dmg, acc, base_stat,
                                                                                              effects))