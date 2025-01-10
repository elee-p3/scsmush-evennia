"""
Commands

Commands describe the input the account can do to the game.

"Command.py" contains commands native to Evennia that SCSMUSH has overriden or modified.
"""
import re
import time

from evennia.server.sessionhandler import SESSIONS
from evennia import ObjectDB, AccountDB
from evennia import default_cmds
from evennia.utils import utils, create, evtable, make_iter, inherits_from, datetime_format
from evennia.comms.models import Msg
from world.scenes.models import Scene, LogEntry
from world.supplemental import *
from server.conf.settings import AUTO_PUPPET_ON_LOGIN, MAX_NR_CHARACTERS
from world.utilities.utilities import logger


def add_participant_to_scene(character, scene):
    '''
    Given a character, checks the given scene's participants for that character and, if
    NOT present, adds the character as a participant to the scene.
    '''

    if scene.participants.filter(pk=character.id):
        return

    scene.participants.add(character)

def prune_sessions(session_list):
    # This function modifies the display of "who" and "+pot" so that, if the same player is connected from multiple
    # devices, their character name is only displayed once to avoid confusion. Admin still see all connected sessions.
    session_chars = [session.puppet.key for session in session_list]  # get a list of just the character names

    unique_chars = set(session_chars)
    positions = []

    for acct in unique_chars:
        # finds positions of character name matches in the session_accounts list
        char_positions = [i for i, x in enumerate(session_chars) if x == acct]

        # add the position of the account entry we want to the positions list
        if len(char_positions) != 1:
            positions.append(char_positions[-1])
        else:
            positions.append(char_positions[0])

    positions.sort()  # since set() unorders the initial list and we want to keep a specific printed order
    pruned_sessions = []

    for pos in positions:
        pruned_sessions.append(session_list[pos])

    return pruned_sessions


def highlight_names(source_character, in_string, self_color, others_color):
    def add_color_tag(name_list, color, text):
        def replace(match):
            return "|" + color + match.group(1) + "|n"

        sorted_name_list = sorted(name_list, key=len, reverse=True)

        match_list = "|".join([re.escape(name) for name in sorted_name_list])

        # find a match in the match_list that's not in the middle of a word
        return re.sub("(?i)(?<![A-Za-z])(%s)(?![A-Za-z])" % match_list, replace, text)

    if self_color is None:
        self_color = "550"

    if others_color is None:
        others_color = "055"

    # find all characters in current room
    char_list = source_character.location.contents_get(exclude=source_character.location.exits)
    char_name_list = []
    self_name_list = [] # These are necessary to color the source character's name separately

    # generate a list of all names of said characters, including aliases
    for character in char_list:
        name_list = [character.key]
        name_list += character.aliases.all()
        char_name_list.append(name_list)
        if character == source_character:
            self_name_list = name_list

    # generate a list of all occurrences of the name in the input string. This will allow us to print the names
    # exactly as they were written, without overriding case
    out_string = in_string
    for char_names in char_name_list:
        if char_names == self_name_list:
            out_string = add_color_tag(char_names, self_color, out_string)
        else:
            out_string = add_color_tag(char_names, others_color, out_string)

    return out_string


def tailored_msg(caller, msg):
    # TODO(RF): called by pose (and say, eventually).
    # Future question: why not @emit? Because pose's first word is the character's name, not part of the msg content?
    # the point of this function is to
    # 1. Get a list of character objects in the room
    # 2. For each character, check whether names should be colored
    # 3. And custom color the names so that the receiving character's name is highlighted a different color
    char_list = caller.location.contents_get(exclude=caller.location.exits)
    for character in char_list:
        everyone_else = caller.location.contents_get(exclude=caller.location.exits)
        everyone_else.remove(character)
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


def update_pose_timer(caller):
    # Update the pose timer if outside of OOC room
    # This assumes that the character's home is the OOC room, which it is by default
    if caller.location != caller.home:
        caller.set_pose_time(time.time())
        caller.set_obs_mode(False)


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
        caller = self.caller
        if not self.args:
            message = "What do you want to do?"
            caller.msg(message)
        else:
            # Update the pose timer if outside of OOC room
            update_pose_timer(caller)

            message = "%s%s" % (caller.name, self.args)
            message = sub_old_ansi(message)

            # Pose uses tailored_msg because its first word is the character's name, which otherwise won't highlight.
            # Currently retaining the commented code below in case we remember what we wanted to do with it.
            tailored_msg(caller, message)
            # msg = highlight_names(self.caller, msg)
            # if character.color_attribute == True
            # self.caller.location.msg_contents(text=(highlight_names(msg), {"type": "pose"}), from_obj=self.caller)
            # else
            # self.caller.location.msg_contents(text=msg, {"type": "pose"}), from_obj=self.caller)

            # If an event is running in the current room, then write to event's log
            # TODO(RF): Make a write_to_event_log function and feed the EntryType in as a parameter
            if caller.location.db.active_event:
                scene = Scene.objects.get(pk=caller.location.db.event_id)
                scene.addLogEntry(LogEntry.EntryType.POSE, self.args, caller)
                add_participant_to_scene(caller, scene)


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
        def print_pose_header(caller):
            # Finds who in a room has poseheaders on and broadcasts the proper pose to each individual.
            # This is only necessary for @emit, as pose and say begin with the character's name.
            char_list = caller.location.contents_get(exclude=caller.location.exits)
            for character in char_list:
                everyone_else = caller.location.contents_get(exclude=caller.location.exits)
                everyone_else.remove(character)
                if character.db.pose_headers_on:
                    caller.location.msg_contents("|c{0}|n has posed:".format(caller.name), exclude=everyone_else)

        caller = self.caller

        # Update the pose timer if outside of OOC room
        update_pose_timer(caller)

        if not self.args:
            string = "Usage: "
            string += "\n@emit[/switches] [<obj>, <obj>, ... =] <message>"
            caller.msg(string)
            return

        # Checking to see who has poseheaders on and showing them who emitted if they do
        print_pose_header(caller)

        # normal emits by players are just sent to the room and tailored to add posecolors
        message = self.args
        message = sub_old_ansi(message)
        tailored_msg(caller, message)

        # TODO: write_to_event_log function, EMIT EntryType
        # If an event is running in the current room, then write to event log
        if caller.location.db.active_event:
            scene = Scene.objects.get(pk=self.caller.location.db.event_id)
            scene.addLogEntry(LogEntry.EntryType.EMIT, message, self.caller)
            add_participant_to_scene(self.caller, scene)

        return


class CmdOOC(default_cmds.MuxCommand):
    # New command; core MUSH functionality; replaces Evennia's wacky OOC command.
    # More details: Evennia's OOC command unpuppets the current character and moves the player to a special room
    # where they (hypothetically?) can puppet a different character and return to the grid. But there's no built-in
    # functionality to actually switch puppeted characters (as far as we could figure out). Also, there's no login
    # menu to choose which character you want to puppet associated with your account. The dev told me we gotta make one.
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

        if speech[0] == ":":
            speech = ("|y<OOC>|n {0} {1}").format(self.caller.name, speech[1:])
        elif speech[0] == ";":
            speech = ("|y<OOC>|n {0}{1}").format(self.caller.name, speech[1:])
        else:
            speech = ("|y<OOC>|n {0} says, \"{1}\"").format(self.caller.name, speech)

        caller.location.msg_contents(
            speech, from_obj=caller, options={"is_pose": True}
        )


class CmdWho(default_cmds.MuxCommand):
    # Overwritten Evennia command. Players see each other's locations now and multiple sessions are pruned.
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
        # Not quite sure how a non-puppeted session can exist - need to dig into this
        all_sessions = [session for session in all_sessions if session.puppet is not None]

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
            # TODO: replace styled_table with evtable?
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


class CmdMail(default_cmds.MuxAccountCommand):
    # Overwritten Evennia command; incorporated MUSH parsing.
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
        # Adding error handling for if there's no body in the message.
        if not message:
            return caller.msg("The message body is empty. No @mail was sent.")
        for recipient in recipients:
            recipient.msg("You have received a new @mail from %s" % caller)
            # MUSH parsing incorporated via sub_old_ansi.
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
                        messageForm.append(self._HEAD_CHAR * self._WIDTH)
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
                        messageForm.append(self._SUB_HEAD_CHAR * self._WIDTH)
                        messageForm.append(message.message)
                        messageForm.append(self._HEAD_CHAR * self._WIDTH)
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
                    header_line_char=self._SUB_HEAD_CHAR,
                    width=self._WIDTH,
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

                self.caller.msg(self._HEAD_CHAR * self._WIDTH)
                self.caller.msg(str(table))
                self.caller.msg(self._HEAD_CHAR * self._WIDTH)
            else:
                self.caller.msg("There are no messages in your inbox.")


class CmdSay(default_cmds.MuxCommand):
    # Overwritten Evennia command; added event code and posecolors (commented out).
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
        update_pose_timer(caller)

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
        # TODO: addLogEntry function for EntryType SAY
        if caller.location.db.active_event:
            scene = Scene.objects.get(pk=self.caller.location.db.event_id)
            scene.addLogEntry(LogEntry.EntryType.SAY, self.args, self.caller)
            add_participant_to_scene(self.caller, scene)


class CmdCharSelect(default_cmds.MuxCommand):
    """
    stop puppeting and go to the character select screen

    Usage:
      charselect

    Go to the character select screen.
    """

    key = "charselect"
    locks = "cmd:pperm(Player)"
    aliases = "unpuppet"
    help_category = "General"

    # this is used by the parent
    # account_caller = True

    def func(self):
        caller = self.caller
        account = caller.account
        session = self.session
        char_name = caller.name

        old_char = account.get_puppet(session)
        if not old_char:
            string = "You are already unpuppeted."
            self.msg(string)
            return

        account.db._last_puppet = old_char

        # disconnect
        try:
            caller.msg("\n|GYou are no longer puppeting {0}.|n\n".format(char_name))
            caller.msg(account.at_look(target=account.characters, session=session))
            account.unpuppet_object(session)

            if AUTO_PUPPET_ON_LOGIN and MAX_NR_CHARACTERS == 1 and self.playable:
                # only one character exists and is allowed - simplify
                caller.msg("You are out-of-character (OOC).\nUse |wic|n to get back into the game.")
                return

        except RuntimeError as exc:
            self.msg(f"|rCould not unpuppet from |c{old_char}|n: {exc}")