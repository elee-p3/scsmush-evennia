from evennia import default_cmds
from evennia.commands import command
from evennia.contrib.rpg.dice import CmdDice, roll_dice
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
      call - request a roll from the target. Multiple targets separated by comma
      cancel - cancel a received call for a roll
      hidden - tell the room the roll is being done, but don't show the result
      secret - don't inform the room about neither roll nor result

    Examples:
      dice 3d6 + 4
      dice 1d100 - 2 < 50
      dice 1d20#Reize rolls saving throw against seasickness
      dice/call reize=1d20-2>=10#Seasickness check
      dice/call reize, ivo=1d20>=10#Bromance check
      (when responding to roll/call) roll+2#Replacing comment with my own

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

    roll/call sends a roll request to another player, useful for DMing.
    The recipient may change the modifier or comment. E.g., if the sender sends
    "roll/call 1d20+1>=10#Goblin attack" and the recipient types "roll +2#Dodge"
    the result will be "roll 1d20+3>=10#Dodge".

    """

    def func(self):
        """Mostly parsing for calling the dice roller function"""

        test_failed = False
        is_rollcall = False
        # example to use for now is "roll 2d6+4<3#testing"
        caller = self.caller
        args = self.args
        if self.check_if_rollcall(args):
            if caller.db.rollcall:
                if args:
                    caller.db.rollcall = self.modify_rollcall(caller.db.rollcall, args)
                args = caller.db.rollcall
                is_rollcall = True
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
            target_list = None
            # Check for multiple targets
            if "," in target:
                target_list = target.split(",")
            if not target_list:
                target_list = [target]
            try:
                roll = split_args[1]
            except IndexError:
                return caller.msg("Please input a target and a roll for +roll/call.")
            for target in target_list:
                target = target.lstrip()
                characters = location_character_search(caller.location)
                # TODO: turn alias_list_in_room function into utility (along with the target_object code below)
                alias_list_in_room = [(character, character.aliases.all()) for character in characters]
                target_alias_list = [idx for idx, alias_tuple in enumerate(alias_list_in_room) if target.lower() in alias_tuple[1]]
                target_object = None
                if target_alias_list:
                    target_alias_idx = target_alias_list[0]
                    target_object = alias_list_in_room[target_alias_idx][0]
                # Find the actual character object using the input string
                # TODO: this is copied code, so refactor and make a function
                for obj in caller.location.contents:
                    if not target_object:
                        if target.lower() in obj.db_key.lower():
                            target_object = obj
                if not target_object:
                    return caller.msg("Your specified target for +roll/call cannot be found in this room.")
                # Use the silent "test" switch to test the roll before sending it off.
                command.Command.execute_cmd(self, raw_string=str("roll/test " + roll))
                if test_failed:
                    return caller.msg("Due to an error with the roll, your +roll/call was not sent to the target.")
                if not target_object.db.rollcall:
                    target_object.db.rollcall = roll
                    target_object.msg(caller.key + " has called for you to roll " + roll + ". Type 'roll' to do so or type"
                                                                                           " 'roll/cancel' to decline.")
                    caller.msg("You called for " + target_object.key + " to make the roll " + roll + ".")
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
            if is_rollcall:
                # Reset rollcall status so character can accept another
                caller.db.rollcall = ""

    def check_if_rollcall(self, roll_string):
        # This is a sub-function meant to confirm if the +roll arg is an actual dice roll (e.g., 3d6+2)
        # or a +roll/call activation (e.g., roll +2). First I'll strip out any comment, then I'll check
        # if there is a "d" in the string, because that would only be true if it's not a +roll/call.
        # Is that hacky? Whatever man!!! Leave me alone!!!
        if "#" in roll_string:
            split_roll_string = roll_string.split("#")
            roll_string = split_roll_string[0]
        # If "d" in roll_string, return False; it's a dice roll. Else, return True; it's a roll/call.
        return not ("d" in roll_string)

    def modify_rollcall(self, rollcall, args):
        # This modifies a rollstring according to the args. E.g., if caller.db.rollcall is 3d6+2, typing
        # roll/call +2 will roll 3d6+4. Also allow for comment to be overwritten. For simplicity, the
        # target number (TN) cannot be modified: for 1d20>=12, the 12 cannot be changed.
        # First, interpret the rollcall.
        split_rollcall = []
        modifier_value = 0
        negative_value = False
        base_roll = ""
        comment = ""
        target_number_string = ""
        if "+" in rollcall:
            split_rollcall = rollcall.split("+")
        if "-" in rollcall:
            split_rollcall = rollcall.split("-")
            negative_value = True
        # If either modifier exists, split_rollcall will now no longer be an empty list.
        if split_rollcall:
            # We want split_rollcall[1], the right side. The modifier might be multiple digits, possibly.
            # So I can't just grab a single index. I'll want to carve out exactly what's between TN/comment, if extant.
            base_roll = split_rollcall[0]
            modifier_side = split_rollcall[1]
            if "#" in modifier_side:
                split_modifier = modifier_side.split("#", 1)
                # Overwrite the modifier without the comment
                modifier_side = split_modifier[0]
                comment = split_modifier[1]
            if ">" in modifier_side:
                split_modifier_side = modifier_side.split(">", 1)
                target_number_string = ">" + split_modifier_side[1]
                modifier_value = int(split_modifier_side[0])
            elif "<" in modifier_side:
                split_modifier_side = modifier_side.split("<", 1)
                target_number_string = "<" + split_modifier_side[1]
                modifier_value = int(split_modifier_side[0])
            else:
                modifier_value = int(modifier_side)
        else:
            # Let's unpack from the right
            base_roll = rollcall
            if "#" in rollcall:
                base_roll = rollcall.split("#", 1)[0]
                comment = rollcall.split("#", 1)[1]
            if ">" in rollcall:
                # Careful not to include the comment in the target number string
                if comment:
                    target_number_string = ">" + base_roll.split(">")[1]
                else:
                    target_number_string = ">" + rollcall.split(">")[1]
                # Then continue to redefine base_roll as the shortest version
                base_roll = rollcall.split(">")[0]
            elif "<" in rollcall:
                if comment:
                    target_number_string = "<" + base_roll.split(">")[1]
                else:
                    target_number_string = "<" + rollcall.split(">")[1]
                base_roll = rollcall.split("<")[0]
        if negative_value:
            modifier_value *= -1
        # Now interpret the args inputted by the character executing "roll."
        if "#" in args:
            # Split once on the hash.
            split_args = args.split("#", 1)
            args = split_args[0]
            comment = split_args[1]
        if "+" in args:
            modifier_value += int(args.split("+")[1])
        if "-" in args:
            modifier_value -= int(args.split("-")[1])
        # Now let's rebuild the roll string
        new_rollstring = base_roll
        if modifier_value > 0:
            new_rollstring += "+" + str(modifier_value)
        if modifier_value < 0:
            # If it's negative, there should already be a minus sign in there
            new_rollstring += str(modifier_value)
        if target_number_string:
            new_rollstring += target_number_string
        if comment:
            new_rollstring += "#" + comment
        return new_rollstring