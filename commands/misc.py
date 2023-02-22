"""
Misc Commands

Misc Commands are either to be possibly replaced with overwritten Evennia commands (@tel instead of warp, desc instead
of setdesc) or are idiosyncratic (roulette and gridscan).

"""
import csv
import random

from evennia import default_cmds, ObjectDB
from evennia.commands import command
from typeclasses.rooms import Room
from world.supplemental import *
from world.utilities.utilities import logger


class CmdWarp(default_cmds.MuxCommand):
    """
    teleport to another location

    Usage:
      warp <target location>

    Examples:
      warp granse - zerhem kingdom

    """

    key = "warp"
    aliases = "+warp"
    locks = "cmd:all()"

    # This is a copy-paste of @tel (or teleport) with reduced functions. @tel is an admin
    # command that takes objects as args, allowing you to teleport objects to places.
    # Warp only allows you to teleport yourself. I chose to make a new command rather than
    # expand on @tel with different permission sets because the docstring/help file is
    # expansive for @tel, as it has many switches in its admin version.
    def func(self):
        """Performs the teleport"""

        caller = self.caller
        args = self.args

        destination = caller.search(args, global_search=True)
        if not destination:
            caller.msg("Destination not found.")
            return
        if destination:
            if not isinstance(destination, Room):
                caller.msg("Destination is not a room.")
                return
            else:
                caller.move_to(destination)
                caller.msg("Teleported to %s." % destination)


class CmdSetDesc(default_cmds.MuxCommand):
    # I made this command because "desc" in Evennia is a builder command with builder permissions.
    # This is similar to why I made +warp as a modified @tel: because @tel was very complex. If I could figure out
    # how to curtail or modify the docstring or automatically generated help file depending on the permissions
    # of the person accessing it, it might be more elegant or make more sense to just have desc and @tel, not setdesc.
    """
    describe yourself

    Usage:
      setdesc <description>

    Add a description to yourself. This
    will be visible to people when they
    look at you.
    """

    key = "setdesc"
    aliases = ["@desc"]
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    # Here I overwrite "setdesc" from the Evennia master so it has an alias, "@desc."
    def func(self):
        """add the description"""

        if not self.args:
            self.caller.msg("You must add a description.")
            return

        message = self.args
        message = sub_old_ansi(message)
        self.caller.db.desc = message
        self.caller.msg("You set your description.")


class CmdRoulette(default_cmds.MuxCommand):
    # Original command; classify as Devin's Wacky Stuff. Maybe useful to other people?
    # The scene types/premises are specific to SCSMUSH's fantasy theme, but in principle, a roulette to help you
    # pick a location for a random scene or something is not totally useless.
    """
    Randomly generate a scene location, scene type or premise, and "fortune."

    If typed without an argument (+roulette), selects any room on the grid,
    excluding OOC-only rooms (e.g., OOC Room). If typed with an argument (+roulette
    <string>), selects any room containing that string.

    Since the names of all IC rooms begin with their region (e.g., "Granse,"
    "Cosmopolis"), use the latter feature to specify a region within which to
    generate a random location. See "roomdesc" for roulette's companion command.

    Usage:
      +roulette
      +roulette granse
    """

    key = "+roulette"
    aliases = ["roulette"]

    def func(self):
        caller = self.caller
        args = self.args
        if not args:
            # Create a list of Room objects that are not the OOC Room, Sparring Room, or World Map.
            ic_locations = [obj for obj in ObjectDB.objects.all() if (obj.id not in [2, 8, 11] and "Room" in obj.db_typeclass_path)]
        if args:
            # Create a list of Room objects that contain the specified string.
            args_list = ObjectDB.objects.filter(db_key__contains=args)
            ic_locations = []
            for obj in args_list:
                if "Room" in obj.db_typeclass_path:
                    ic_locations.append(obj)
            if not ic_locations:
                return caller.msg("No location name containing the specified string was found.")
        # Randomly select the key of a IC room.
        ic_location = random.choice(ic_locations)
        # First, print the name of the selected location as a string.
        self.caller.location.msg_contents("{} spins the Scene Roulette.".format(caller.key))
        self.caller.location.msg_contents("|wThe wheel of fate is turning...|n")
        self.caller.location.msg_contents("Location: " + ic_location.db_key)
        # Second, roll 1d20 to pull from a list of scene types or premises.
        type_roll = random.randint(1, 20)
        if type_roll == 1:
            self.caller.location.msg_contents("Type: |rWild Card.|n A shocking and transformative event occurs.")
        elif type_roll in range(2, 6):
            self.caller.location.msg_contents("Type: |yCombat.|n Defeat your foe(s).")
        elif type_roll in range(6, 10):
            self.caller.location.msg_contents("Type: |gSocial.|n Get to know each other better.")
        elif type_roll in range(10, 12):
            self.caller.location.msg_contents("Type: |cInvestigation.|n Seek knowledge or solve a mystery.")
        elif type_roll in range(12, 14):
            self.caller.location.msg_contents("Type: |gGathering.|n Acquire new resources.")
        elif type_roll in range(14, 16):
            self.caller.location.msg_contents("Type: |yEscape.|n Elude some hazard or pursuer.")
        elif type_roll in range(16, 18):
            self.caller.location.msg_contents("Type: |cPursuit.|n Hunt down an elusive target.")
        elif type_roll in range(18, 20):
            self.caller.location.msg_contents("Type: |yTraining.|n Practice a skill or technique.")
        else:
            self.caller.location.msg_contents("Type: |rDate.|n Increase your Affection Meters.")
        # Third, roll 1d20 to pull from a list of "fortunes."
        fortune_roll = random.randint(1, 20)
        if fortune_roll in range(1, 3):
            self.caller.location.msg_contents("The party's luck will be |rcatastrophically bad.|n Somehow, it's all Reize's fault.")
        elif fortune_roll in range(3, 8):
            self.caller.location.msg_contents("The party's luck will be |ybad.|n But grit and finesse may still see you through!")
        elif fortune_roll in range(8, 14):
            self.caller.location.msg_contents("The party's luck will be |caverage.|n The result could go either way.")
        elif fortune_roll in range(14, 19):
            self.caller.location.msg_contents("The party's luck will be |ggood.|n Something exciting and beneficial will happen.")
        else:
            self.caller.location.msg_contents("The party's luck will be |wextraordinarily good.|n An event akin to a miracle will occur!")


class CmdRoomDesc(default_cmds.MuxCommand):
    # Original command riffing off of Gridscan that's actually meant to be useful for players using +roulette.
    """
    This command displays the description of any room on the grid with the
    specified name. When using "roulette," use "roomdesc" to check the
    random room's description for help in developing a premise for a scene.

    Usage:
      +roomdesc <string>
    """
    key = "roomdesc"
    aliases = "+roomdesc"
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        if not args:
            # Create a list of Room objects that are not the OOC Room, Sparring Room, or World Map.
            return caller.msg("Please include a string contained in the name of a specific room.")
        if args:
            # Create a list of Room objects that contain the specified string.
            args_list = ObjectDB.objects.filter(db_key__contains=args)
            ic_locations = []
            for obj in args_list:
                if "Room" in obj.db_typeclass_path:
                    ic_locations.append(obj)
            if not ic_locations:
                return caller.msg("No location name containing the specified string was found.")
            if len(args_list) > 1:
                return caller.msg("Multiple possible locations were found. Please try a longer string.")
            else:
                return caller.msg("The description of " + ic_locations[0].key + " is: \n\n" + ic_locations[0].db.desc)


class CmdGridscan(default_cmds.MuxCommand):
    # Original command. Literally only I care about this. I used it like twice.
    """
    This is a command to print all of the room names and descs
    to check if I have repeated any turns of phrase. I just want
    to be able to read all my room descs in one place.

    Usage:
      +gridscan
    """
    key = "+gridscan"
    aliases = ["gridscan"]
    locks = "cmd:perm(Admin)"

    def func(self):
        caller = self.caller
        # Create a list of Room objects that are not the OOC Room, Sparring Room, or World Map.
        ic_locations = [obj for obj in ObjectDB.objects.all() if (obj.id not in [2, 8, 11] and "Room" in obj.db_typeclass_path)]
        for location in ic_locations:
            caller.msg("ID: " + str(location.id) + " --- Name: " + location.db_key)
            caller.msg("Desc: " + location.db.desc + "\n")


class CmdResetCombatFile(default_cmds.MuxCommand):
    """
    Deletes and recreates csv file for collecting combat data

    Usage:
    """
    key = "+clearcombat"
    locks = "cmd:perm(Admin)"
    def func(self):
        with open("combat_record.csv", "w", encoding='UTF8') as combat_csv:
            csvwriter = csv.writer(combat_csv)
            csvwriter.writerow(["attacker name",
                                "power",
                                "knowledge",
                                "defender name",
                                "parry",
                                "barrier",
                                "speed",
                                "block penalty",
                                "endure bonus",
                                "final action",
                                "weaving",
                                "bracing",
                                "baiting",
                                "rushing",
                                "attack name",
                                "AP cost",
                                "attack dmg",
                                "attack acc",
                                "attack stat",
                                "attack effects",
                                "AIM OR FEINT",
                                "reaction name",
                                "success",
                                "final damage"])
        self.caller.msg("Cleared combat log")


class CmdTeach(default_cmds.MuxCommand):
    # Original command that some MU*s have to display both input and output.
    """
    Display the input for a command before executing it. Used to teach others
    how to execute commands.

    Usage:
      +teach <command>
    """
    key = "teach"
    aliases = "+teach"
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        if not args:
            return caller.msg("Error: teach must be followed by a separate command to execute.")
        # Display the input to the room.
        caller.location.msg_contents(caller.key + " |yinputs|n: " + str(args))
        # Use Evennia's "execute_cmd" method to execute the args as a separate command.
        caller.location.msg_contents("This |youtputs|n:")
        command.Command.execute_cmd(self, raw_string=str(args))
        # TODO: Would be nice if, when the command doesn't exist, teach doesn't run. Review cmdhandler.py.