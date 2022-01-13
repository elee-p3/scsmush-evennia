from evennia.contrib.dice import CmdDice,roll_dice
import re

RE_PARTS = re.compile(r"(d|\+|-|/|\*|<=|>=|<|>|!=|==)")
RE_MOD = re.compile(r"(\+|-|/|\*)")
RE_COND = re.compile(r"(<=|>=|<|>|!=|==)")
RE_COMMENT = re.compile(r"(#)")

class CmdSCSDice(CmdDice):
    def func(self):
        """Mostly parsing for calling the dice roller function"""

        # example to use for now is "roll 2d6+4<3#testing"
        if not self.args:
            self.caller.msg("Usage: @dice <nr>d<sides> [modifier] [conditional]#comment")
            return
        argstring = "".join(str(arg) for arg in self.args)

        # check for a comment and preprocess the string to remove the comment
        comment = ""
        roll_string = ""
        comment_parts = [part for part in RE_COMMENT.split(self.args) if part]
        # check if there is a comment at all. This will catch when there isn't specifically a hashtag+string
        if len(comment_parts) == 3:
            comment = comment_parts[2]  # in theory, the last element of the list should be the comment string

        roll_string = comment_parts[0] # everything outside of the hashtag and comment should be the actual roll.
        # note that the first element of comment_parts will *always* be the roll string with or without a hashtag

        roll_string = roll_string.rstrip()
        comment = comment.lstrip()
        parts = [part for part in RE_PARTS.split(roll_string) if part]
        len_parts = len(parts)
        modifier = None
        conditional = None

        if len_parts < 3 or parts[1] != "d":
            self.caller.msg(
                "You must specify the die roll(s) as <nr>d<sides>."
                " For example, 2d6 means rolling a 6-sided die 2 times."
            )
            return

        # Limit the number of dice and sides a character can roll to prevent server slow down and crashes
        ndicelimit = 10000  # Maximum number of dice
        nsidelimit = 10000  # Maximum number of sides
        if int(parts[0]) > ndicelimit or int(parts[2]) > nsidelimit:
            self.caller.msg("The maximum roll allowed is %sd%s." % (ndicelimit, nsidelimit))
            return

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
            self.caller.msg("You must specify a valid die roll")
            return
        # do the roll
        try:
            result, outcome, diff, rolls = roll_dice(
                ndice, nsides, modifier=modifier, conditional=conditional, return_tuple=True
            )
        except ValueError:
            self.caller.msg(
                "You need to enter valid integer numbers, modifiers and operators."
                " |w%s|n was not understood." % self.args
            )
            return
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
        else:
            # normal roll
            string = yourollstring % (roll_string, "")
            self.caller.msg(string)
            string = roomrollstring % (self.caller.key, roll_string, "")
            self.caller.location.msg_contents(string, exclude=self.caller)
            # print only if comment exists
            if comment:
                string = "|214Comment:|n {0}".format(comment)
                self.caller.location.msg_contents(string)
            string = resultstring % (rolls, result)
            string += outcomestring
            self.caller.location.msg_contents(string)