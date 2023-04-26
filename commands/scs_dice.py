from evennia import default_cmds
from evennia.commands import command
from evennia.contrib.dice import CmdDice,roll_dice
import re
from world.scenes.models import Scene, LogEntry
from world.utilities.utilities import location_character_search

RE_PARTS = re.compile(r"(d|\+|-|/|\*|<=|>=|<|>|!=|==)")
RE_MOD = re.compile(r"(\+|-|/|\*)")
RE_COND = re.compile(r"(<=|>=|<|>|!=|==)")
RE_COMMENT = re.compile(r"(#)")

class CmdSCSDice(CmdDice):
    """
    roll dice

    Usage:
      dice[/switch] <nr>d<sides> [modifier] [success condition] #[comment]

    Switch:
      call - request a roll from the target
      cancel - cancel a received call for a roll
      hidden - tell the room the roll is being done, but don't show the result
      secret - don't inform the room about neither roll nor result

    Examples:
      dice 3d6 + 4
      dice 1d100 - 2 < 50
      dice 1d20#Reize rolls saving throw against seasickness
      dice/call reize=1d20-2>=10#Seasickness check

    This will roll the given number of dice with given sides and modifiers.
    So e.g. 2d6 + 3 means to 'roll a 6-sided die 2 times and add the result,
    then add 3 to the total'.
    Accepted modifiers are +, -, * and /.
    A success condition is given as normal Python conditionals
    (<,>,<=,>=,==,!=). So e.g. 2d6 + 3 > 10 means that the roll will succeed
    only if the final result is above 8. If a success condition is given, the
    outcome (pass/fail) will be echoed along with how much it succeeded/failed
    with. The hidden/secret switches will hide all or parts of the roll from
    everyone but the person rolling.

    To add a comment string to be displayed to the room to contextualize
    the roll, place a hashtag (#) at the end of the command and write a sentence.

    """

    def func(self):
        """Mostly parsing for calling the dice roller function"""

        test_failed = False
        reset_rollcall = False
        # example to use for now is "roll 2d6+4<3#testing"
        caller = self.caller
        args = self.args
        if not args:
            if caller.db.rollcall:
                args = caller.db.rollcall
                reset_rollcall = True
            else:
                if "test" in self.switches:
                    test_failed = True
                else:
                    return caller.msg("Usage: @dice <nr>d<sides> [modifier] [conditional]#comment")
        if "cancel" in self.switches:
            caller.db.rollcall = ""
            return caller.msg("You have canceled the called roll and cleared your roll queue.")
        argstring = "".join(str(arg) for arg in args)

        # check for a comment and preprocess the string to remove the comment
        comment = ""
        roll_string = ""
        comment_parts = [part for part in RE_COMMENT.split(args) if part]
        caller.msg(comment_parts)
        # check if there is a comment at all. This will catch when there isn't specifically a hashtag+string
        if len(comment_parts) == 3:
            comment = comment_parts[2]  # in theory, the last element of the list should be the comment string

        roll_string = comment_parts[0] # everything outside of the hashtag and comment should be the actual roll.
        # note that the first element of comment_parts will *always* be the roll string with or without a hashtag

        roll_string = roll_string.rstrip()
        comment = comment.lstrip()
        # if this is a roll/call, strip the target out of the first part of roll_string
        if "call" in self.switches:
            roll_string = roll_string.split("=", 1)[1]
        parts = [part for part in RE_PARTS.split(roll_string) if part]
        len_parts = len(parts)
        modifier = None
        conditional = None

        if len_parts < 3 or parts[1] != "d":
            if "test" in self.switches:
                test_failed = True
            else:
                return caller.msg(
                    "You must specify the die roll(s) as <nr>d<sides>."
                    " For example, 2d6 means rolling a 6-sided die 2 times."
                )

        # Limit the number of dice and sides a character can roll to prevent server slow down and crashes
        ndicelimit = 10000  # Maximum number of dice
        nsidelimit = 10000  # Maximum number of sides
        try:
            if int(parts[0]) > ndicelimit or int(parts[2]) > nsidelimit:
                if "test" in self.switches:
                    test_failed = True
                else:
                    return self.caller.msg("The maximum roll allowed is %sd%s." % (ndicelimit, nsidelimit))
        except ValueError:
            if "test" in self.switches:
                test_failed = True
            else:
                return caller.msg("You must specify a valid die roll. (ValueError)")

        # TODO: Make it possible to type, e.g., "roll +2" and do a rollcall but modified, or "roll #Horray!" and
        # modify the comment. This requires identifying and swapping out (or adding) specific parts of the dice string.
        ndice, nsides = parts[0], parts[2]
        if len_parts == 3:
            # just something like 1d6
            pass
        elif len_parts == 5:
            # either e.g. 1d6 + 3  or something like 1d6 > 3
            if parts[3] in ("+", "-", "*", "/"):
                modifier = (parts[3], parts[4])
            else:  # assume it is a conditional
                conditional = (parts[3], parts[4])
        elif len_parts == 7:
            # the whole sequence, e.g. 1d6 + 3 > 5
            modifier = (parts[3], parts[4])
            conditional = (parts[5], parts[6])
        else:
            # error
            if "test" in self.switches:
                test_failed = True
            else:
                return caller.msg("You must specify a valid die roll. (len_parts error)")
        # do the roll
        try:
            result, outcome, diff, rolls = roll_dice(
                ndice, nsides, modifier=modifier, conditional=conditional, return_tuple=True
            )
        except ValueError:
            if "test" in self.switches:
                test_failed = True
            else:
                return caller.msg(
                    "You need to enter valid integer numbers, modifiers and operators."
                    " |w%s|n was not understood." % args
                )
        # format output
        if len(rolls) > 1:
            rolls = ", ".join(str(roll) for roll in rolls[:-1]) + " and " + str(rolls[-1])
        else:
            rolls = rolls[0]
        if outcome is None:
            outcomestring = ""
        elif outcome:
            outcomestring = " This is a |gsuccess|n (by %s)." % diff
        else:
            outcomestring = " This is a |rfailure|n (by %s)." % diff
        yourollstring = "You roll %s%s."
        roomrollstring = "%s rolls %s%s."
        resultstring = " Roll(s): %s. Total result is |w%s|n."

        if "secret" in self.switches:
            # don't echo to the room at all
            string = yourollstring % (argstring, " (secret, not echoed)")
            string += "\n" + resultstring % (rolls, result)
            string += outcomestring + " (not echoed)"
            self.caller.msg(string)
        elif "hidden" in self.switches:
            # announce the roll to the room, result only to caller
            string = yourollstring % (argstring, " (hidden)")
            self.caller.msg(string)
            string = roomrollstring % (self.caller.key, argstring, " (hidden)")
            self.caller.location.msg_contents(string, exclude=self.caller)
            # handle result
            string = resultstring % (rolls, result)
            string += outcomestring + " (not echoed)"
            self.caller.msg(string)
        elif "test" in self.switches:
            pass
        elif "call" in self.switches:
            # Roll/call is used to send a request for a roll to another player, e.g., by a DM
            if not args:
                return caller.msg("Please input a target and a roll for +roll/call.")
            split_args = args.split("=", 1)
            target = split_args[0]
            try:
                roll = split_args[1]
            except IndexError:
                return caller.msg("Please input a target and a roll for +roll/call.")
            characters = location_character_search(caller.location)
            # TODO: add alias_list_in_room to a utility?
            # alias_list_in_room = [(character, character.aliases.all()) for character in characters]
            # target_alias_list = [idx for idx, alias_tuple in enumerate(alias_list_in_room) if target.lower() in alias_tuple[1]]
            target_object = None
            # if target_alias_list:
            #     target_alias_idx = target_alias_list[0]
            #     target_object = alias_list_in_room[target_alias_idx][0]
            if target not in [character.key for character in characters]:
                return caller.msg("Your specified target for +roll/call cannot be found in this room.")
            # Find the actual character object using the input string
            # TODO: this is copied code, so refactor and make a function
            # target_object = None
            for obj in caller.location.contents:
                if not target_object:
                    if target in obj.db_key:
                        target_object = obj
            # Use the silent "test" switch to test the roll before sending it off.
            command.Command.execute_cmd(self, raw_string=str("roll/test " + roll))
            if test_failed:
                return caller.msg("Due to an error with the roll, your +roll/call was not sent to the target.")
            if not target_object.db.rollcall:
                target_object.db.rollcall = roll
                target_object.msg(caller.key + " has called for you to roll " + roll + ". Type 'roll' to do so.")
            else:
                return caller.msg("The target has an outstanding +roll/call and cannot receive another.")
        else:
            # normal roll
            logstring = ""
            # logstring collects all the log-relevant dice roll strings
            string = yourollstring % (roll_string, "")
            self.caller.msg(string)
            string = roomrollstring % (self.caller.key, roll_string, "")
            self.caller.location.msg_contents(string, exclude=self.caller)
            logstring = string
            # print only if comment exists
            if comment:
                string = "|MComment:|n {0}".format(comment)
                self.caller.location.msg_contents(string)
                logstring += "|/" + string
            string = resultstring % (rolls, result)
            string += outcomestring
            self.caller.location.msg_contents(string)
            logstring += "|/" + string
            # If an event is running in the current room, then write to event's log
            if self.caller.location.db.active_event:
                scene = Scene.objects.get(pk=self.caller.location.db.event_id)
                scene.addLogEntry(LogEntry.EntryType.DICE, logstring, self.caller)
            if reset_rollcall:
                caller.db.rollcall = ""