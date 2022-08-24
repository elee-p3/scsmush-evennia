from world.combat.normals import NORMALS
from evennia import default_cmds
from world.utilities.utilities import location_character_search
import random
from world.combat.combat_math import damage_calc

def append_to_queue(caller, target, attack):
    # Find the actual attack object using the input attack string
    # TODO: it's just the normals for now, but we'll concatenate a full list of attacks once characters have their own custom attacks
    # TODO: the caller isn't used yet, but in the future we might modify attacks by the current character's equipment/stats
    attack_object = None
    for normal in NORMALS:
        if attack == normal:
            attack_object = normal
            caller.msg(normal)
            break

    # append a tuple per attack: (id, attack)
    # TODO: have a think about what happens when a player removes an attack out of order. e.g if you have three attacks and remove #2, then the next time you append another attack you'll have two attacks labelled (3, something)
    # TODO: one possible way would be to stick the id generation in a while loop and make sure that the id is unique by incrementing until it is
    target.db.queue.append({"id":len(target.db.queue)+1, "attack":attack_object})

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
        split_args = args.split('=')
        target = split_args[0].lower() # make everything case-insensitive
        action = split_args[1].lower()

        caller.msg(target)
        caller.msg(action)

        # First, check that the character attacking has more than 0 LF
        char = self.caller.get_abilities()
        if char["lf"] <= 0:
            return caller.msg("Your character is KOed and cannot attack!")

        # Then check that the target is a character in the room using utility
        characters_in_room = location_character_search(location)
        caller.msg(characters_in_room)
        if target not in [character.name.lower() for character in characters_in_room]:
            return caller.msg("Your target is not a character in this room.")

        # Find the actual character object using the input string
        target_object = None
        for obj in location.contents:
            if target in obj.db_key.lower():
                target_object = obj

        # Now check that the action is an attack, which for now is just normals.
        if action not in NORMALS:
            return caller.msg("Your selected action cannot be found.")

        # If the target is here and the action exists, then we add the attack to the target's queue.
        # The attack should be assigned an ID based on its place in the queue.
        # I figure a queue should be a list and the ID should be the attack's index +1.
        # Check if the "queue" attribute exists and, if not, create an empty list first.
        if target_object.db.queue is None:
            target_object.db.queue = []

        append_to_queue(caller, target_object, action)
        caller.msg("You attacked {target} with {action}.".format(target=target_object, action=action))

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
        caller = self.caller
        if not caller.db.queue is None:
            caller.msg([attack["attack"].name for attack in self.caller.db.queue]) # ignore the ids, only print out the attacks
        else:
            caller.msg("Nothing in queue")

class CmdDodge(default_cmds.MuxCommand):
    """
        Avoid Mad Dog. Though you cannot.

        Usage:
          +dodge

    """

    key = "+dodge"
    aliases = ["dodge"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        idx = 0

        # Syntax is just "dodge <id>".
        if not isinstance(args, str):
            return caller.msg("Please input the attack name as a string.")
        else:
            idx = int(args)-1
            if idx < 0:
                caller.msg("That ID is not in the queue")
                return

        if int(args) not in [attack["id"] for attack in caller.db.queue]:
            return caller.msg("Cannot find that attack in your queue.")

        # The attack is a string in the queue. Flip a coin and remove the attack from the queue.
        attack = caller.db.queue[idx]["attack"] # -1 since we're using normal person indices here
        random100 = random.randint(1, 100)
        if attack.acc > random100:
            final_damage = damage_calc(attack.dmg, attack.base_stat, caller.db.parry, caller.db.barrier)
            caller.msg("You have been hit by {attack}! Oh, God! Mad Dog!!!!!".format(attack=args))
            caller.msg("You took {dmg} damage".format(dmg=final_damage))
            caller.db.lf -= final_damage
        else:
            caller.msg("You have successfully dodged. Good for you.")

        del caller.db.queue[idx]