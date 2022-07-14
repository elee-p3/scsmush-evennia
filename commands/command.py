"""
Commands

Commands describe the input the account can do to the game.

"""
from math import floor
#from typing import AwaitableGenerator
from evennia.server.sessionhandler import SESSIONS
import time
import re
from evennia import ObjectDB, AccountDB
from evennia import default_cmds
from evennia.utils import utils, create, evtable, make_iter, inherits_from, datetime_format
from evennia.comms.models import Msg
from world.scenes.models import Scene, LogEntry
from typeclasses.rooms import Room
from world.supplemental import *

from datetime import datetime

def add_participant_to_scene(character, scene):
    '''
    Given a character, checks the given scene's participants for that character and, if
    NOT present, adds the character as a participant to the scene.
    '''

    if scene.participants.filter(pk=character.id):
        return

    scene.participants.add(character)

# Danny was here, bitches.
# text replacement function stolen from https://stackoverflow.com/questions/919056/case-insensitive-replace
def ireplace(old, repl, text):
    # This function is used in highlight_names to replace names: it is not case sensitive but maintains case.
    return re.sub('(?i)'+re.escape(old), lambda m: repl, text)

def prune_sessions(session_list):
    # This function modifies the display of "who" and "+pot" so that, if the same player is connected from multiple
    # devices, their character name is only displayed once to avoid confusion. Admin still see all connected sessions.
    session_accounts = [session.account.key for session in session_list]  # get a list of just the names

    unique_accounts = set(session_accounts)
    positions = []

    for acct in unique_accounts:
        # finds positions of account name matches in the session_accounts list
        account_positions = [i for i, x in enumerate(session_accounts) if x == acct]

        # add the position of the account entry we want to the positions list
        if len(account_positions) != 1:
            positions.append(account_positions[-1])
        else:
            positions.append(account_positions[0])

    positions.sort()  # since set() unorders the initial list and we want to keep a specific printed order
    pruned_sessions = []

    for pos in positions:
        pruned_sessions.append(session_list[pos])

    return pruned_sessions

def highlight_names(source_character, in_string, self_color, others_color):
    # This function is used in tailored_msg.
    if self_color is None:
        self_color = "550"

    if others_color is None:
        others_color = "055"

    # find all characters in current room
    char_list = source_character.location.contents_get(exclude=source_character.location.exits)
    name_list = []
    self_name_list = [] # These are necessary to color the source character's name separately
    full_list = []
    self_full_list = []

    # generate a list of all names of said characters, including aliases
    for character in char_list:
        name_list.append(character.key)
        name_list += character.aliases.all()
        if character == source_character:
            self_name_list.append(character.key)
            self_name_list += character.aliases.all()

    # generate a list of all occurrences of the name in the input string. This will allow us to print the names
    # exactly as they were written, without overriding case
    for name in name_list:
        full_list += re.findall(re.compile(re.escape(name), re.IGNORECASE), in_string)
        if name in self_name_list:
            self_full_list += re.findall(re.compile(re.escape(name), re.IGNORECASE), in_string)

    out_string = in_string
    # for each of the names in the list, replace the string with a colored version
    for name in full_list:
        if name in self_full_list:
            out_string = ireplace(name, "|" + self_color + name + "|n", out_string)
        else:
            out_string = ireplace(name, "|" + others_color + name + "|n", out_string)

    return out_string

def tailored_msg(caller, msg):
    # the point of this function is to
    # 1. Get a list of character objects in the room
    # 2. For each character, check whether names should be colored
    # 3. And custom color the names so that the receiving character's name is highlighted a different color
    char_list = caller.location.contents_get(exclude=caller.location.exits)
    # for char in char_list:
    #     caller.msg("{0}".format(char))

    for character in char_list:
        everyone_else = caller.location.contents_get(exclude=caller.location.exits)
        everyone_else.remove(character)
        # for char in everyone_else:
        #     caller.msg("{0}".format(char))
        # caller.msg("pose_colors_self for {0} is {1}".format(character, character.db.pose_colors_self))
        # caller.msg("pose_colors_others for {0} is {1}".format(character, character.db.pose_colors_others))
        # caller.msg("pose_colors_on for {0} is {1}".format(character, character.db.pose_colors_on))

        if character.db.pose_colors_on:
            caller.location.msg_contents(text=(highlight_names(character, msg, character.db.pose_colors_self,
                                                                    character.db.pose_colors_others),
                                                    {"type": "pose"}),
                                              exclude=everyone_else,
                                              from_obj=caller)
        else:
            caller.location.msg_contents(text=(msg, {"type": "pose"}),
                                              exclude=everyone_else,
                                              from_obj=caller)
    return

class CmdFinger(default_cmds.MuxCommand):
    """
        +finger
        Usage:
          +finger <character>
        Displays finger'd character's information
        """

    key = '+finger'
    aliases = ["finger", "oocfinger", "+oocfinger"]
    locks = "cmd:all()"

    def func(self):
        if not self.args:
            # TODO: better messaging
            self.caller.msg("Need a person to finger!")
            return

        # We've tried changing the evennia-master code in evennia/objects/object.py to allow for non-exact string
        # matching with global_search=True, but this seems to cause "examine <db_id>" to fail
        # TODO: figure out a way to have partial string matching AND db_id referencing. Might be able to do this with more playing around with the if-else logic in objects.py
        target = self.caller.search(self.args, global_search=True)

        # TODO: actually figure out error handling. Need to be able to differentiate between "ambiguous search" error and "not a character" error
        try:
            char = target.get_abilities()
            charInfoTable = evtable.EvTable(border_left_char="|", border_right_char="|", border_top_char="-",
                                            border_bottom_char=" ", width=78)
            charInfoTable.add_column()
            charInfoTable.add_column()
            charInfoTable.add_row("Sex: {0}".format(char["sex"]), "Group: {0}".format(char["group"]))
            charInfoTable.add_row("Race: {0}".format(char["race"]), "Domain: {0}".format(char["domain"]))
            charInfoTable.add_row("Origin: {0}".format(char["origin"]), "Element: {0}".format(char["element"]))

            charDescTable = evtable.EvTable(border="table", border_left_char="|", border_right_char="|",
                                            border_top_char="-",
                                            border_bottom_char="_", width=78)
            charDescTable.add_column()
            charDescTable.add_row('"{0}"'.format(char["quote"]))
            charDescTable.add_row("")
            charDescTable.add_row("{0}".format(char["profile"]))

            fingerMsg = ""
            fingerMsg += "/\\" + 74 * "_" + "/\\" + "\n"

            # TODO: we want if-else logic to add an alias if they have it, and just spit out their name if they don't
            nameBorder = "\\/" + (37 - floor(len(char["name"] + " - " + char["occupation"]) / 2.0)) * " "
            nameBorder += char["name"] + " - " + char["occupation"]
            nameBorder += (76 - len(nameBorder)) * " " + "\\/"
            fingerMsg += nameBorder + "\n"

            charInfoString = charInfoTable.__str__()
            fingerMsg += charInfoString[:charInfoString.rfind('\n')] + "\n"  # delete last newline (i.e. bottom border)
            fingerMsg += charDescTable.__str__() + "\n"
            fingerMsg += "/\\" + 74 * "_" + "/\\" + "\n"
            fingerMsg += "\\/" + 74 * " " + "\\/" + "\n"

            self.caller.msg(fingerMsg)
        except:
            self.caller.msg("Target is either not a character or there are multiple matches")


class CmdPose(default_cmds.MuxCommand):
    """
    strike a pose
    Usage:
      pose <pose text>
      pose's <pose text>
    Example:
      pose is standing by the wall, smiling.
       -> others will see:
      Tom is standing by the wall, smiling.
    Describe an action being taken. The pose text will
    automatically begin with your name.
    """

    key = "pose"
    aliases = [":", "emote"]
    locks = "cmd:all()"

    def parse(self):
        """
        Custom parse the cases where the emote
        starts with some special letter, such
        as 's, at which we don't want to separate
        the caller's name and the emote with a
        space.
        """
        args = self.args
        if args and not args[0] in ["'", ",", ":"]:
            args = " %s" % args.strip()
        self.args = args

    def func(self):
        """Hook function"""
        if not self.args:
            message = "What do you want to do?"
            self.caller.msg(message)
        else:
            # Update the pose timer if outside of OOC room
            # This assumes that the character's home is the OOC room, which it is by default
            if self.caller.location != self.caller.home:
                self.caller.set_pose_time(time.time())
                self.caller.set_obs_mode(False)

            message = "%s%s" % (self.caller.name, self.args)
            message = sub_old_ansi(message)

            tailored_msg(self.caller, message)
            # msg = highlight_names(self.caller, msg)
            # if character.color_attribute == True
            # self.caller.location.msg_contents(text=(highlight_names(msg), {"type": "pose"}), from_obj=self.caller)
            # else
            # self.caller.location.msg_contents(text=msg, {"type": "pose"}), from_obj=self.caller)

            # If an event is running in the current room, then write to event's log
            if self.caller.location.db.active_event:
                scene = Scene.objects.get(pk=self.caller.location.db.event_id)
                scene.addLogEntry(LogEntry.EntryType.POSE, self.args, self.caller)
                add_participant_to_scene(self.caller, scene)

class CmdEmit(default_cmds.MuxCommand):
    """
    @emit
    Usage:
      @emit[/switches] [<obj>, <obj>, ... =] <message>
      @remit           [<obj>, <obj>, ... =] <message>
      @pemit           [<obj>, <obj>, ... =] <message>
    Switches:
      room : limit emits to rooms only (default)
      players : limit emits to players only
      contents : send to the contents of matched objects too
    Emits a message to the selected objects or to
    your immediate surroundings. If the object is a room,
    send to its contents. @remit and @pemit are just
    limited forms of @emit, for sending to rooms and
    to players respectively.
    """

    key = "@emit"
    aliases = ["@pemit", "@remit", "\\\\"]
    locks = "cmd:all()"
    help_category = "Social"
    perm_for_switches = "Builders"
    arg_regex = None

    def get_help(self, caller, cmdset):
        """Returns custom help file based on caller"""
        if caller.check_permstring(self.perm_for_switches):
            return self.__doc__
        help_string = """
        @emit
        Usage :
            @emit <message>
        Emits a message to your immediate surroundings. This command is
        used to provide more flexibility than the structure of poses, but
        please remember to indicate your character's name.
        """
        return help_string

    def func(self):
        """Implement the command"""

        caller = self.caller

        # Update the pose timer if outside of OOC room
        # This assumes that the character's home is the OOC room, which it is by default
        if caller.location != caller.home:
            caller.set_pose_time(time.time())
            caller.set_obs_mode(False)

        if not self.args:
            string = "Usage: "
            string += "\n@emit[/switches] [<obj>, <obj>, ... =] <message>"
            caller.msg(string)
            return

        # normal emits by players are just sent to the room and tailored to add posecolors
        message = self.args
        message = sub_old_ansi(message)
        tailored_msg(caller, message)

        # If an event is running in the current room, then write to event log
        if caller.location.db.active_event:
            scene = Scene.objects.get(pk=self.caller.location.db.event_id)
            scene.addLogEntry(LogEntry.EntryType.EMIT, message, self.caller)
            add_participant_to_scene(self.caller, scene)
        return

class CmdOOC(default_cmds.MuxCommand):
    """
    speak out-of-character
    Usage:
      ooc <message>
    Talk to those in your current location.
    """

    key = "ooc"
    aliases = ["+ooc"]
    locks = "cmd:all()"

    def func(self):
        """Run the OOC command"""

        caller = self.caller

        if not self.args:
            home = caller.home
            if not home:
                caller.msg("Mysteriously, you cannot return to the OOC Room.")
            elif home == caller.location:
                caller.msg("You are already in the OOC Room.")
            else:
                caller.msg("You return whence you came.")
                caller.move_to(home)
            return

        speech = self.args

        # Calling the at_before_say hook on the character
        speech = caller.at_before_say(speech)

        # If speech is empty, stop here
        if not speech:
            return

        # Call the at_after_say hook on the character
        # caller.at_say(speech, msg_self=True)
        if speech[0] == ":":
            speech = ("|y<OOC>|n {0} {1}").format(self.caller.name, speech[1:])
        elif speech[0] == ";":
            speech = ("|y<OOC>|n {0}{1}").format(self.caller.name, speech[1:])
        else:
            speech = ("|y<OOC>|n {0} says, \"{1}\"").format(self.caller.name, speech)

        caller.location.msg_contents(
            speech, from_obj=caller, options={"is_pose": True}
        )

class CmdSheet(default_cmds.MuxCommand):
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
            "implements the actual functionality"
            # TODO: We did this before we knew about the evtable function. This needs to be refactored.
            char = self.caller.get_abilities()
            # name, sex, race, occupation, group, domain, element, origin, quote, profile, lf, maxlf, ap, maxap, ex, maxex, \
            # power, knowledge, parry, barrier, speed = self.caller.get_abilities()
            sheetMsg = ""

            sheetMsg += "/\\" + 74 * "_" + "/\\" + "\n"
            nameBorder = "\\/" + (37 - floor(len(char["name"] + " - " + char["occupation"])/2.0)) * " "
            nameBorder += char["name"] + " - " + char["occupation"]
            nameBorder += (76 - len(nameBorder))*" " + "\\/"
            sheetMsg += nameBorder + "\n"
            sheetMsg += "--" + 74 * "-" + "--" + "\n"

            # first row
            firstRow = "| LF"
            firstRow += (22 - (len(str(char["lf"])) + len(str(char["maxlf"])) + 1 + len(firstRow))) * " "
            firstRow += "{0}/{1}".format(char["lf"], char["maxlf"])
            firstRow = self.padToSecondLabel(firstRow)
            firstRow += "Power"
            firstRow = self.padToLastValue(firstRow)
            firstRow += "{0}".format(char["power"])
            firstRow = self.padToEnd(firstRow)
            firstRow += "\n"
            sheetMsg += firstRow

            # second row
            secondRow = "| ["
            secondRow += (21 - len(secondRow)) * " "
            secondRow += "]"
            secondRow = self.padToSecondLabel(secondRow)
            secondRow += "Knowledge"
            secondRow = self.padToLastValue(secondRow)
            secondRow += "{0}".format(char["knowledge"])
            secondRow = self.padToEnd(secondRow)
            secondRow += "\n"
            sheetMsg += secondRow

            # third row
            thirdRow = "| AP"
            thirdRow += (22 - (len(str(char["ap"])) + len(str(char["maxap"])) + 1 + len(thirdRow))) * " "
            thirdRow += "{0}/{1}".format(char["ap"], char["maxap"])
            thirdRow = self.padToSecondLabel(thirdRow)
            thirdRow += "Parry"
            thirdRow = self.padToLastValue(thirdRow)
            thirdRow += "{0}".format(char["parry"])
            thirdRow = self.padToEnd(thirdRow)
            thirdRow += "\n"
            sheetMsg += thirdRow

            # fourth row
            fourthRow = "| ["
            fourthRow += (21 - len(fourthRow)) * " "
            fourthRow += "]"
            fourthRow = self.padToSecondLabel(fourthRow)
            fourthRow += "Barrier"
            fourthRow = self.padToLastValue(fourthRow)
            fourthRow += "{0}".format(char["barrier"])
            fourthRow = self.padToEnd(fourthRow)
            fourthRow += "\n"
            sheetMsg += fourthRow

            # fifth row
            fifthRow = "| EX"
            fifthRow += (20 - (len(str(char["ex"])) + len(str(char["maxex"])) + 1 + len(fifthRow))) * " "
            fifthRow += "{0}%/{1}%".format(char["ex"], char["maxex"])
            fifthRow = self.padToSecondLabel(fifthRow)
            fifthRow += "Speed"
            fifthRow = self.padToLastValue(fifthRow)
            fifthRow += "{0}".format(char["speed"])
            fifthRow = self.padToEnd(fifthRow)
            fifthRow += "\n"
            sheetMsg += fifthRow

            # sixth row
            sixthRow = "| ["
            sixthRow += (21 - len(sixthRow)) * " "
            sixthRow += "]"
            sixthRow = self.padToEnd(sixthRow)
            sixthRow += "\n"
            sheetMsg += sixthRow

            # ARTTSSSSS
            sheetMsg += "|===================================ARTS=====================================|\n"


            # Bottom border
            sheetMsg += "/\\" + 74 * "_" + "/\\" + "\n"
            sheetMsg += "\\/" + 74 * " " + "\\/" + "\n"

            self.caller.msg(sheetMsg)


        def padToSecondLabel(self, inString):
            outString = inString + (38 - len(inString)) * " "
            return outString


        def padToLastValue(self, inString):
            outString = inString + (63 - len(inString)) * " "
            return outString


        def padToEnd(self, inString):
            """Pad out to the end of the sheet row"""
            outString = inString + (77 - len(inString))*" "
            outString += "|"
            return outString

        # def sheetRow(self, firstLabel, firstValue, secondLabel, secondValue):
        #     """Format a row of the sheet, providing the sheet the two values that you want to print"""
        #
        #     # 80 characters total per row
        #     rowString = "|"
        #     rowString += 10 * " "
        #     rowString += firstLabel + ": "
        #     rowString += firstValue
        #     rowString += (50-size(rowString)) * " " # pad out to second column
        #
        #     # if we want a second value (i.e. if there are an even number of values in the sheet)
        #     if secondColumn:
        #         rowString += secondLabel+": "
        #         rowString += secondValue
        #
        #     # remember to leave room for the right border
        #     rowString += 79 - size(rowString) * " "
        #     rowString += "|"
        #
        #     return rowString

class CmdSetDesc(default_cmds.MuxCommand):
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

class CmdWho(default_cmds.MuxCommand):
    """
    list who is currently online

    Usage:
      who
      doing
      where

    Shows who is currently online. Doing is an alias that limits info
    also for those with all permissions. Modified to allow players to see
    the locations of other players and add a "where" alias.
    """

    key = "who"
    aliases = ["doing", "where"]
    locks = "cmd:all()"

    # this is used by the parent
    account_caller = True

    # Here we have modified "who" to display the locations of players to other players
    # and to add "where" as an alias.
    def func(self):
        """
        Get all connected accounts by polling session.
        """

        account = self.account
        all_sessions = SESSIONS.get_sessions()

        all_sessions = sorted(all_sessions, key=lambda o: o.account.key) # sort sessions by account name
        pruned_sessions = prune_sessions(all_sessions)

        # check if users are admins and should be able to see all users' session data
        if self.cmdstring == "doing":
            show_session_data = False
        else:
           show_session_data = account.check_permstring("Developer") or account.check_permstring(
               "Admins"
           )

        naccounts = SESSIONS.account_count()
        if show_session_data:
            # privileged info
            table = self.styled_table(
                "|wAccount Name",
                "|wOn for",
                "|wIdle",
                "|wPuppeting",
                "|wRoom",
                "|wCmds",
                "|wProtocol",
                "|wHost",
            )
            for session in all_sessions:
                if not session.logged_in:
                    continue
                delta_cmd = time.time() - session.cmd_last_visible
                delta_conn = time.time() - session.conn_time
                session_account = session.get_account()
                puppet = session.get_puppet()
                location = puppet.location.key if puppet and puppet.location else "None"
                table.add_row(
                    utils.crop(session_account.get_display_name(account), width=25),
                    utils.time_format(delta_conn, 0),
                    utils.time_format(delta_cmd, 1),
                    utils.crop(puppet.get_display_name(account) if puppet else "None", width=25),
                    utils.crop(location, width=35),
                    session.cmd_total,
                    session.protocol_key,
                    isinstance(session.address, tuple) and session.address[0] or session.address,
                )
        else:
            # unprivileged
            table = self.styled_table("|wAccount name", "|wOn for", "|wIdle", "|wRoom")
            for session in pruned_sessions:
                if not session.logged_in:
                    continue
                delta_cmd = time.time() - session.cmd_last_visible
                delta_conn = time.time() - session.conn_time
                session_account = session.get_account()
                puppet = session.get_puppet()
                location = puppet.location.key if puppet and puppet.location else "None"
                table.add_row(
                    utils.crop(session_account.get_display_name(account), width=25),
                    utils.time_format(delta_conn, 0),
                    utils.time_format(delta_cmd, 1),
                    utils.crop(location, width=35),
                )
        is_one = naccounts == 1
        self.msg(
            "|wAccounts:|n\n%s\n%s unique account%s logged in."
            % (table, "One" if is_one else naccounts, "" if is_one else "s")
        )

class CmdPot(default_cmds.MuxCommand):
    """
    View the pose tracker (pot). The pose tracker displays the name,
    time connected, time idle, and time since last posed of every
    character in the room, ordered starting with whomever posed
    longest ago. Thus, during an ongoing scene, the person whose
    turn it is to pose will appear at the top of the list.

    Those who have not posed are listed below all those who have.
    To signify that you are leaving an ongoing scene, type +observe
    to reset your pose timer and move to the bottom (see "help observe").

    Usage:
      +pot

    """

    key = "+pot"
    aliases = ["pot"]
    locks = "cmd:all()"

    # this is used by the parent
    account_caller = True

    def func(self):
        """
        Get all connected accounts by polling session.
        """

        account = self.account
        all_sessions = SESSIONS.get_sessions()

        all_sessions = sorted(all_sessions, key=lambda o: o.account.character.get_pose_time()) # sort by last posed time
        pruned_sessions = prune_sessions(all_sessions)

        naccounts = SESSIONS.account_count()
        table = self.styled_table(
            "|wCharacter",
            "|wOn for",
            "|wIdle",
            "|wLast posed"
        )

        old_session_list = []

        for session in pruned_sessions:
            if not session.logged_in:
                continue

            session_account = session.get_account()
            puppet = session.get_puppet()
            delta_cmd = time.time() - session.cmd_last_visible
            delta_conn = time.time() - session.conn_time
            delta_pose_time = time.time() - puppet.get_pose_time()

            if delta_pose_time > 3600:
                old_session_list.append(session)
                continue

            if puppet.location == self.caller.character.location:
                # logic for setting up pose table
                table.add_row(puppet.key,
                              utils.time_format(delta_conn, 0),
                              utils.time_format(delta_cmd, 1),
                              utils.time_format(delta_pose_time, 1))

        for session in old_session_list:
            session_account = session.get_account()
            puppet = session.get_puppet()
            delta_cmd = time.time() - session.cmd_last_visible
            delta_conn = time.time() - session.conn_time
            delta_pose_time = time.time() - puppet.get_pose_time()

            if puppet.location == self.caller.character.location:
                if puppet.get_obs_mode() == True:
                    table.add_row("|y" + puppet.key + " (O)",
                                  utils.time_format(delta_conn, 0),
                                  utils.time_format(delta_cmd, 1),
                                  "-")
                else:
                    table.add_row(puppet.key,
                                  utils.time_format(delta_conn, 0),
                                  utils.time_format(delta_cmd, 1),
                                  "-")

        self.caller.msg(table)

class CmdObserve(default_cmds.MuxCommand):
    """
        Enter observer mode. This signifies that you are observing,
        and not participating, in a scene. In +pot, you will be
        displayed at the bottom of the list with an "(O)" before
        your name. If you have previously posed, your pose timer
        will also be reset.

        If your character is leaving an ongoing scene, +observe
        will help to  prevent anyone accidentally waiting on a pose
        from you.

        Usage:
          +observe

    """

    key = "+observe"
    aliases = ["observe"]
    locks = "cmd:all()"

    def func(self):
        self.caller.set_pose_time(0.0)
        self.caller.set_obs_mode(True)
        self.msg("Entering observer mode.")
        self.caller.location.msg_contents(
            "|y<SCENE>|n {0} is now an observer.".format(self.caller.name))

class CmdMail(default_cmds.MuxAccountCommand):
    """
    Communicate with others by sending mail.

    Usage:
      @mail       - Displays all the mail an account has in their mailbox
      @mail <#>   - Displays a specific message
      @mail <accounts>=<subject>/<message>
              - Sends a message to the comma separated list of accounts.
      @mail/delete <#> - Deletes a specific message
      @mail/forward <account list>=<#>[/<Message>]
              - Forwards an existing message to the specified list of accounts,
                original message is delivered with optional Message prepended.
      @mail/reply <#>=<message>
              - Replies to a message #. Prepends message to the original
                message text.
    Switches:
      delete  - deletes a message
      forward - forward a received message to another object with an optional message attached.
      reply   - Replies to a received message, appending the original message to the bottom.
    Examples:
      @mail 2
      @mail Griatch=New mail/Hey man, I am sending you a message!
      @mail/delete 6
      @mail/forward feend78 Griatch=4/You guys should read this.
      @mail/reply 9=Thanks for the info!

    """

    key = "@mail"
    aliases = ["mail"]
    lock = "cmd:all()"
    help_category = "General"

    # These used to be global settings in the original code, but nothing else needs access to them.
    _HEAD_CHAR = "|015-|n"
    _SUB_HEAD_CHAR = "-"
    _WIDTH = 78

    # This is the @mail command from contrib. We have added MUSH parsing to sending @mail.
    def parse(self):
        """
        Add convenience check to know if caller is an Account or not since this cmd
        will be able to add to either Object- or Account level.

        """
        super().parse()
        self.caller_is_account = bool(
            inherits_from(self.caller, "evennia.accounts.accounts.DefaultAccount")
        )

    def search_targets(self, namelist):
        """
        Search a list of targets of the same type as caller.

        Args:
            caller (Object or Account): The type of object to search.
            namelist (list): List of strings for objects to search for.

        Returns:
            targetlist (Queryset): Any target matches.

        """
        nameregex = r"|".join(r"^%s$" % re.escape(name) for name in make_iter(namelist))
        if self.caller_is_account:
            matches = AccountDB.objects.filter(username__iregex=nameregex)
        else:
            matches = ObjectDB.objects.filter(db_key__iregex=nameregex)
        return matches

    def get_all_mail(self):
        """
        Returns a list of all the messages where the caller is a recipient. These
            are all messages tagged with tags of the `mail` category.

        Returns:
            messages (QuerySet): Matching Msg objects.

        """
        if self.caller_is_account:
            return Msg.objects.get_by_tag(category="mail").filter(db_receivers_accounts=self.caller)
        else:
            return Msg.objects.get_by_tag(category="mail").filter(db_receivers_objects=self.caller)

    def send_mail(self, recipients, subject, message, caller):
        """
        Function for sending new mail.  Also useful for sending notifications
        from objects or systems.

        Args:
            recipients (list): list of Account or Character objects to receive
                the newly created mails.
            subject (str): The header or subject of the message to be delivered.
            message (str): The body of the message being sent.
            caller (obj): The object (or Account or Character) that is sending the message.

        """
        for recipient in recipients:
            recipient.msg("You have received a new @mail from %s" % caller)
            new_message = create.create_message(
                self.caller, sub_old_ansi(message), receivers=recipient, header=subject
            )
            new_message.tags.add("new", category="mail")

        if recipients:
            caller.msg("You sent your message.")
            return
        else:
            caller.msg("No valid target(s) found. Cannot send message.")
            return

    def func(self):
        """
        Do the events command functionality
        """

        subject = ""
        body = ""

        if self.switches or self.args:
            if "delete" in self.switches or "del" in self.switches:
                try:
                    if not self.lhs:
                        self.caller.msg("No Message ID given. Unable to delete.")
                        return
                    else:
                        all_mail = self.get_all_mail()
                        mind_max = max(0, all_mail.count() - 1)
                        mind = max(0, min(mind_max, int(self.lhs) - 1))
                        if all_mail[mind]:
                            mail = all_mail[mind]
                            question = "Delete message {} ({}) [Y]/N?".format(mind + 1, mail.header)
                            ret = yield (question)
                            # handle not ret, it will be None during unit testing
                            if not ret or ret.strip().upper() not in ("N", "No"):
                                all_mail[mind].delete()
                                self.caller.msg("Message %s deleted" % (mind + 1,))
                            else:
                                self.caller.msg("Message not deleted.")
                        else:
                            raise IndexError
                except IndexError:
                    self.caller.msg("That message does not exist.")
                except ValueError:
                    self.caller.msg("Usage: @mail/delete <message ID>")
            elif "forward" in self.switches or "fwd" in self.switches:
                try:
                    if not self.rhs:
                        self.caller.msg(
                            "Cannot forward a message without a target list. " "Please try again."
                        )
                        return
                    elif not self.lhs:
                        self.caller.msg("You must define a message to forward.")
                        return
                    else:
                        all_mail = self.get_all_mail()
                        mind_max = max(0, all_mail.count() - 1)
                        if "/" in self.rhs:
                            message_number, message = self.rhs.split("/", 1)
                            mind = max(0, min(mind_max, int(message_number) - 1))

                            if all_mail[mind]:
                                old_message = all_mail[mind]

                                self.send_mail(
                                    self.search_targets(self.lhslist),
                                    "FWD: " + old_message.header,
                                    message
                                    + "\n---- Original Message ----\n"
                                    + old_message.message,
                                    self.caller,
                                )
                                self.caller.msg("Message forwarded.")
                            else:
                                raise IndexError
                        else:
                            mind = max(0, min(mind_max, int(self.rhs) - 1))
                            if all_mail[mind]:
                                old_message = all_mail[mind]
                                self.send_mail(
                                    self.search_targets(self.lhslist),
                                    "FWD: " + old_message.header,
                                    "\n---- Original Message ----\n" + old_message.message,
                                    self.caller,
                                )
                                self.caller.msg("Message forwarded.")
                                old_message.tags.remove("new", category="mail")
                                old_message.tags.add("fwd", category="mail")
                            else:
                                raise IndexError
                except IndexError:
                    self.caller.msg("Message does not exist.")
                except ValueError:
                    self.caller.msg("Usage: @mail/forward <account list>=<#>[/<Message>]")
            elif "reply" in self.switches or "rep" in self.switches:
                try:
                    if not self.rhs:
                        self.caller.msg("You must define a message to reply to.")
                        return
                    elif not self.lhs:
                        self.caller.msg("You must supply a reply message")
                        return
                    else:
                        all_mail = self.get_all_mail()
                        mind_max = max(0, all_mail.count() - 1)
                        mind = max(0, min(mind_max, int(self.lhs) - 1))
                        if all_mail[mind]:
                            old_message = all_mail[mind]
                            self.send_mail(
                                old_message.senders,
                                "RE: " + old_message.header,
                                self.rhs + "\n---- Original Message ----\n" + old_message.message,
                                self.caller,
                            )
                            old_message.tags.remove("new", category="mail")
                            old_message.tags.add("-", category="mail")
                            return
                        else:
                            raise IndexError
                except IndexError:
                    self.caller.msg("Message does not exist.")
                except ValueError:
                    self.caller.msg("Usage: @mail/reply <#>=<message>")
            else:
                # normal send
                if self.rhs:
                    if "/" in self.rhs:
                        subject, body = self.rhs.split("/", 1)
                    else:
                        body = self.rhs
                    self.send_mail(self.search_targets(self.lhslist), subject, body, self.caller)
                else:
                    all_mail = self.get_all_mail()
                    mind_max = max(0, all_mail.count() - 1)
                    try:
                        mind = max(0, min(mind_max, int(self.lhs) - 1))
                        message = all_mail[mind]
                    except (ValueError, IndexError):
                        self.caller.msg("'%s' is not a valid mail id." % self.lhs)
                        return

                    messageForm = []
                    if message:
                        messageForm.append(_HEAD_CHAR * _WIDTH)
                        messageForm.append(
                            "|wFrom:|n %s" % (message.senders[0].get_display_name(self.caller))
                        )
                        # note that we cannot use %-d format here since Windows does not support it
                        day = message.db_date_created.day
                        messageForm.append(
                            "|wSent:|n %s"
                            % message.db_date_created.strftime(f"%b {day}, %Y - %H:%M:%S")
                        )
                        messageForm.append("|wSubject:|n %s" % message.header)
                        messageForm.append(_SUB_HEAD_CHAR * _WIDTH)
                        messageForm.append(message.message)
                        messageForm.append(_HEAD_CHAR * _WIDTH)
                    self.caller.msg("\n".join(messageForm))
                    message.tags.remove("new", category="mail")
                    message.tags.add("-", category="mail")

        else:
            # list messages
            messages = self.get_all_mail()

            if messages:
                table = evtable.EvTable(
                    "|wID|n",
                    "|wFrom|n",
                    "|wSubject|n",
                    "|wArrived|n",
                    "",
                    table=None,
                    border="header",
                    header_line_char=_SUB_HEAD_CHAR,
                    width=_WIDTH,
                )
                index = 1
                for message in messages:
                    status = str(message.db_tags.last().db_key.upper())
                    if status == "NEW":
                        status = "|gNEW|n"

                    table.add_row(
                        index,
                        message.senders[0].get_display_name(self.caller),
                        message.header,
                        datetime_format(message.db_date_created),
                        status,
                    )
                    index += 1

                table.reformat_column(0, width=6)
                table.reformat_column(1, width=18)
                table.reformat_column(2, width=34)
                table.reformat_column(3, width=13)
                table.reformat_column(4, width=7)

                self.caller.msg(_HEAD_CHAR * _WIDTH)
                self.caller.msg(str(table))
                self.caller.msg(_HEAD_CHAR * _WIDTH)
            else:
                self.caller.msg("There are no messages in your inbox.")

class CmdSay(default_cmds.MuxCommand):
    """
    speak as your character

    Usage:
      say <message>

    Talk to those in your current location.
    """

    key = "say"
    aliases = ['"', "'"]
    locks = "cmd:all()"

    # Here we overwrite the default "say" command so that it updates the pose timer for +pot,
    # as well as for LogEntry, etc.
    def func(self):
        """Run the say command"""

        caller = self.caller

        # Update the pose timer if outside of OOC room
        # This assumes that the character's home is the OOC room, which it is by default
        if caller.location != caller.home:
            caller.set_pose_time(time.time())
            caller.set_obs_mode(False)

        if not self.args:
            caller.msg("Say what?")
            return

        message = self.args

        # Calling the at_before_say hook on the character
        message = caller.at_before_say(message)
        # tailored_msg(caller, message)
        # TODO: Apply tailored_msg to the first person/third person distinction in say display.

        # If speech is empty, stop here
        if not message:
            return

        # Call the at_after_say hook on the character
        caller.at_say(message, msg_self=True)

        # If an event is running in the current room, then write to event log
        if caller.location.db.active_event:
            scene = Scene.objects.get(pk=self.caller.location.db.event_id)
            scene.addLogEntry(LogEntry.EntryType.SAY, self.args, self.caller)
            add_participant_to_scene(self.caller, scene)

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

class CmdEvent(default_cmds.MuxCommand):
    """
    The @event command is used to log scenes.

    Usage:
            @event/start: Create a scene and begin logging poses in the current room.
            @event/stop: Stop the log currently running in the room.
            @event/info: Display the current log's ID number, name, etc.
            @event/name [string]: Set the current log's name as [string].
            @event/desc [string]: Set the current log's desc as [string].
    """

    key = "@event"
    aliases = ["event", "@scene", "scene"]
    locks = "cmd:all()"

    def is_running(self):
        # Check that there is a log running.
        caller = self.caller
        is_running = True
        if not caller.location.db.active_event:
            caller.msg("There is no active event running in this room.")
            is_running = False
            return is_running

    def are_args(self):
        # Check that the user has inputted a string.
        caller = self.caller
        are_args = True
        if not self.args:
            caller.msg("Name the log description what?")
            are_args = False
            return are_args

    def find_event(self):
        # Find the scene object that matches the scene/event reference on the
        # location.
        caller = self.caller
        try:
            events = Scene.objects.filter(id=caller.location.db.event_id).get()
        except Exception as original:
            raise Exception("Found zero or multiple Scenes :/") from original
        return events

    def func(self):
        caller = self.caller

        if not self.switches:
            caller.msg("You must add a switch, like '@event/start' or '@event/stop'.")
            return

        elif "start" in self.switches:
            # Make sure the current room doesn't already have an active event, and otherwise mark it
            if caller.location.db.active_event:
                caller.msg("There is currently an active event running in this room already.")
                return
            caller.location.db.active_event = True
            event = Scene.objects.create(
                name='Unnamed Event',
                start_time=datetime.now(),
                description='Placeholder description of scene plz change k thx bai',
                location=caller.location,
            )

            caller.msg("DEBUG: this event has the following information:\nname = {0}\ndescription = {1}\nlocation = {2}\nid = {3}".format(event.name, event.description, event.location, event.id))

            caller.location.db.event_id = event.id

            self.caller.location.msg_contents("|y<SCENE>|n A log has been started in this room with scene ID {0}.".format(event.id))
            return

        elif "stop" in self.switches:
            # Make sure the current room's event hasn't already been stopped
            if not self.is_running():
                return

            events = self.find_event()

            # Stop the Room's active event by removing the active event attribute.
            Scene.objects.filter(id=caller.location.db.event_id).update(end_time=datetime.now())
            self.caller.location.msg_contents("|y<SCENE>|n A log has been stopped in this room with scene ID {0}.".format(events.id))
            del caller.location.db.active_event
            return

        elif "info" in self.switches:
            if not self.is_running():
                return

            events = self.find_event()

            caller.msg("This event has the following information:\nName = {0}\nDescription = {1}\nLocation = {2}\nID = {3}".format(events.name, events.description, events.location, events.id))

        elif "name" in self.switches:
            if not self.is_running():
                return

            if not self.are_args():
                return

            Scene.objects.filter(id=caller.location.db.event_id).update(name=self.args)
            caller.msg("Scene name set.")

        elif "desc" in self.switches:
            if not self.is_running():
                return

            if not self.are_args():
                return

            Scene.objects.filter(id=caller.location.db.event_id).update(description=self.args)
            caller.msg("Scene description set.")

class CmdPoseColors(default_cmds.MuxCommand):
    """
    Toggle colored names in poses. Posecolors/self and
    posecolors/others are used to set the colors of one's
    own name and other names, respectively. Type "color
    xterm256" to see the list of eligible color codes.

    Usage:
      posecolors on/off
      posecolors/self <xterm256 code>
      posecolors/others <xterm256 code>

    Examples:
      posecolors on
      posecolors/self 555
      posecolors/others 155

    """

    key = "posecolors"
    aliases = "+posecolors"
    switch_options = ("self", "others")
    locks = "cmd:all()"

    def func(self):
        """Changes pose colors"""

        caller = self.caller
        args = self.args
        switches = self.switches

        if switches or args:
            if args == "on":
                caller.db.pose_colors_on = True
                caller.msg("Name highlighting enabled")
            elif args == "off":
                caller.db.pose_colors_on = False
                caller.msg("Name highlighting disabled")
            elif "self" in switches:
                if len(args) == 3 and args.isdigit:
                    caller.db.pose_colors_self = str(args)
                    caller.msg("Player's name highlighting color updated")
            elif "others" in switches:
                if len(args) == 3 and args.isdigit:
                    caller.db.pose_colors_self = str(args)
                    caller.msg("Other's name highlighting color updated")
            else:
                caller.msg("Unknown switch/argument!")
                return

class CmdPage(default_cmds.MuxCommand):
    """
    send a private message to another account

    Usage:
      page[/switches] [<account>,<account>,... = <message>]
      tell        ''
      page <number>

    Switch:
      last - shows who you last messaged
      list - show your last <number> of tells/pages (default)

    Send a message to target user (if online). If no
    argument is given, you will get a list of your latest messages.
    """

    key = "page"
    aliases = ["tell", "p"]
    switch_options = ("last", "list")
    locks = "cmd:not pperm(page_banned)"
    help_category = "Comms"
    # This is a modified version of the page command that notifies recipients of pages
    # when there are multiple recipients, i.e., when you are in a group conversation.
    # By default, Evennia's page command doesn't inform you that multiple people have
    # received a page that you have received, for some very strange reason!

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Implement function using the Msg methods"""

        # Since account_caller is set above, this will be an Account.
        caller = self.caller

        # get the messages we've sent (not to channels)
        pages_we_sent = Msg.objects.get_messages_by_sender(caller, exclude_channel_messages=True)
        # get last messages we've got
        pages_we_got = Msg.objects.get_messages_by_receiver(caller)

        if "last" in self.switches:
            if pages_we_sent:
                recv = ",".join(obj.key for obj in pages_we_sent[-1].receivers)
                self.msg("You last paged |c%s|n:%s" % (recv, pages_we_sent[-1].message))
                return
            else:
                self.msg("You haven't paged anyone yet.")
                return

        if not self.args or not self.rhs:
            pages = pages_we_sent + pages_we_got
            pages = sorted(pages, key=lambda page: page.date_created)

            number = 5
            if self.args:
                try:
                    number = int(self.args)
                except ValueError:
                    self.msg("Usage: tell [<account> = msg]")
                    return

            if len(pages) > number:
                lastpages = pages[-number:]
            else:
                lastpages = pages
            to_template = "|w{date}{clr} {sender}|nto{clr}{receiver}|n:> {message}"
            from_template = "|w{date}{clr} {receiver}|nfrom{clr}{sender}|n:< {message}"
            listing = []
            prev_selfsend = False
            for page in lastpages:
                multi_send = len(page.senders) > 1
                multi_recv = len(page.receivers) > 1
                sending = self.caller in page.senders
                # self-messages all look like sends, so we assume they always
                # come in close pairs and treat the second of the pair as the recv.
                selfsend = sending and self.caller in page.receivers
                if selfsend:
                    if prev_selfsend:
                        # this is actually a receive of a self-message
                        sending = False
                        prev_selfsend = False
                    else:
                        prev_selfsend = True

                clr = "|c" if sending else "|g"

                sender = f"|n,{clr}".join(obj.key for obj in page.senders)
                receiver = f"|n,{clr}".join([obj.name for obj in page.receivers])
                if sending:
                    template = to_template
                    sender = f"{sender} " if multi_send else ""
                    receiver = f" {receiver}" if multi_recv else f" {receiver}"
                else:
                    template = from_template
                    receiver = f"{receiver} " if multi_recv else ""
                    sender = f" {sender} " if multi_send else f" {sender}"

                listing.append(
                    template.format(
                        date=utils.datetime_format(page.date_created),
                        clr=clr,
                        sender=sender,
                        receiver=receiver,
                        message=page.message,
                    )
                )
            lastpages = "\n ".join(listing)

            if lastpages:
                string = "Your latest pages:\n %s" % lastpages
            else:
                string = "You haven't paged anyone yet."
            self.msg(string)
            return

        # We are sending. Build a list of targets

        if not self.lhs:
            # If there are no targets, then set the targets
            # to the last person we paged.
            if pages_we_sent:
                receivers = pages_we_sent[-1].receivers
            else:
                self.msg("Who do you want to page?")
                return
        else:
            receivers = self.lhslist

        recobjs = []
        for receiver in set(receivers):
            if isinstance(receiver, str):
                pobj = caller.search(receiver)
            elif hasattr(receiver, "character"):
                pobj = receiver
            else:
                self.msg("Who do you want to page?")
                return
            if pobj:
                recobjs.append(pobj)
        if not recobjs:
            self.msg("Noone found to page.")
            return

        header = "|c%s|n |wpages|n" % caller.key # Ivo pages Headwiz, Ugen: <message>
        message = self.rhs

        # if message begins with a :, we assume it is a 'page-pose'
        if message.startswith(":"):
            message = "%s %s" % (caller.key, message.strip(":").strip())

        # create the persistent message object
        create.create_message(caller, message, receivers=recobjs)

        # tell the accounts they got a message.
        received = []
        rstrings = []
        namelist = ""
        for count, pobj in enumerate(recobjs):
            if count == 0:
                namelist += "|c{0}|n".format(pobj.name)
            else:
                namelist += ", |c{0}|n".format(pobj.name)

        for pobj in recobjs:
            if not pobj.access(caller, "msg"):
                rstrings.append("You are not allowed to page %s." % pobj)
                continue
            pobj.msg("%s %s: %s" % (header, namelist, message))
            if hasattr(pobj, "sessions") and not pobj.sessions.count():
                received.append("|C%s|n" % pobj.name)
                rstrings.append(
                    "%s is offline. They will see your message if they list their pages later."
                    % received[-1]
                )
            else:
                received.append("|c%s|n" % pobj.name)
        if rstrings:
            self.msg("\n".join(rstrings))
        self.msg("You paged %s with: '%s'." % (", ".join(received), message))