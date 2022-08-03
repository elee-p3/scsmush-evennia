from world.combat.normals import NORMALS
from evennia import default_cmds
from world.utilities.utilities import location_character_search
import random

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
        target = split_args[0]
        action = split_args[1]
        # First, check that the target is a character in the room using utility
        characters_in_room = location_character_search(location)
        caller.msg(characters_in_room)
        if target not in [character.name for character in characters_in_room]:
            return caller.msg("Your target is not a character in this room.")
        target_object = None
        for obj in location.contents:
            if target in obj.db_key:
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
        target_object.db.queue.append(action)
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
        caller.msg(self.caller.db.queue)

class CmdDodge(default_cmds.MuxCommand):
    """
        Avoid Mad Dog.

        Usage:
          +dodge

    """

    key = "+dodge"
    aliases = ["dodge"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        # Syntax is just "dodge (attack)". Will be ID, can just be string now.
        if not isinstance(args, str):
            return caller.msg("Please input the attack name as a string.")
        if args not in caller.db.queue:
            return caller.msg("Cannot find that attack in your queue.")
        # The attack is a string in the queue. Flip a coin and remove the attack from the queue.
        coin_flip = random.randint(1, 2)
        if coin_flip == 1:
            caller.msg("You have been hit by {attack}! Oh, God! Mad Dog!!!!!".format(attack=args))
        if coin_flip == 2:
            caller.msg("You have successfully dodged. Good for you.")
        caller.db.queue.remove(args)