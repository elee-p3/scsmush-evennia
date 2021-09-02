"""
Commands

Commands describe the input the account can do to the game.

"""
from math import floor
from evennia.commands.command import Command as BaseCommand
from evennia.utils import evtable
from evennia import default_cmds
from evennia.server.sessionhandler import SESSIONS
import time
import re
from evennia import ObjectDB, AccountDB
from evennia import default_cmds
from evennia.utils import utils, create, evtable, make_iter, inherits_from, datetime_format
from evennia.comms.models import Msg

class CmdFinger(default_cmds.MuxCommand):
    """
        +finger
        Usage:
          +finger <character>
        Displays finger'd character's information
        """

    key = '+finger'
    locks = "cmd:all()"

    def func(self):

        # character = self.caller.search(charName, global_search=True) # do we want to search the entire DB?
        target = self.caller.search("Ivo Galvan", global_search=True)

        # name, sex, race, occupation, group, domain, element, quote, profile, lf, maxlf, ap, maxap, ex, maxex, \
        # power, knowledge, parry, barrier, speed = self.caller.get_abilities()

        # char = self.caller.get_abilities()
        char = target.get_abilities()

        charInfoTable = evtable.EvTable(border_left_char="|", border_right_char="|", border_top_char="-",
                                        border_bottom_char=" ", width=78)
        charInfoTable.add_column()
        charInfoTable.add_column()
        charInfoTable.add_row("Sex: {0}".format(char["sex"]), "Group: {0}".format(char["group"]))
        charInfoTable.add_row("Race: {0}".format(char["race"]), "Domain {0}".format(char["domain"]))
        charInfoTable.add_row("Occupation: {0}".format(char["occupation"]), "Element: {0}".format(char["element"]))


        charDescTable = evtable.EvTable(border="table", border_left_char="|", border_right_char="|", border_top_char="-",
                                        border_bottom_char="_", width=78)
        charDescTable.add_column()
        charDescTable.add_row('"{0}"'.format(char["quote"]))
        charDescTable.add_row("{0}".format(char["profile"]))


        fingerMsg = ""
        fingerMsg += "/\\" + 74 * "_" + "/\\" + "\n"

        # TODO: we want if-else logic to add an alias if they have it, and just spit out their name if they don't
        nameBorder = "\\/" + (37 - floor(len(char["name"] + " - " + char["occupation"]) / 2.0)) * " "
        nameBorder += char["name"] + " - " + char["occupation"]
        nameBorder += (76 - len(nameBorder)) * " " + "\\/"
        fingerMsg += nameBorder + "\n"

        # fingerMsg = charInfoTable.__str__() + "\n" + charDescTable.__str__()
        fingerMsg += charInfoTable.__str__() + "\n"
        fingerMsg += charDescTable.__str__() + "\n"
        fingerMsg += "/\\" + 74 * "_" + "/\\" + "\n"
        fingerMsg += "\\/" + 74 * " " + "\\/" + "\n"

        self.caller.msg(fingerMsg)



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

    def sub_old_ansi(self, text):
        """Replacing old ansi with newer evennia markup strings"""
        if not text:
            return ""
        text = text.replace("%r", "|/")
        text = text.replace("%R", "|/")
        text = text.replace("%t", "|-")
        text = text.replace("%T", "|-")
        text = text.replace("%b", "|_")
        text = text.replace("%cr", "|r")
        text = text.replace("%cR", "|[R")
        text = text.replace("%cg", "|g")
        text = text.replace("%cG", "|[G")
        text = text.replace("%cy", "|!Y")
        text = text.replace("%cY", "|[Y")
        text = text.replace("%cb", "|!B")
        text = text.replace("%cB", "|[B")
        text = text.replace("%cm", "|!M")
        text = text.replace("%cM", "|[M")
        text = text.replace("%cc", "|!C")
        text = text.replace("%cC", "|[C")
        text = text.replace("%cw", "|!W")
        text = text.replace("%cW", "|[W")
        text = text.replace("%cx", "|!X")
        text = text.replace("%cX", "|[X")
        text = text.replace("%ch", "|h")
        text = text.replace("%cn", "|n")
        return text

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
        if caller.check_permstring(self.perm_for_switches):
            args = self.args
        else:
            args = self.raw.lstrip(" ")

        if not args:
            string = "Usage: "
            string += "\n@emit[/switches] [<obj>, <obj>, ... =] <message>"
            string += "\n@remit           [<obj>, <obj>, ... =] <message>"
            string += "\n@pemit           [<obj>, <obj>, ... =] <message>"
            caller.msg(string)
            return

        rooms_only = "rooms" in self.switches
        players_only = "players" in self.switches
        send_to_contents = "contents" in self.switches
        perm = self.perm_for_switches
        normal_emit = False

        # we check which command was used to force the switches
        if (
            self.cmdstring == "@remit" or self.cmdstring == "@pemit"
        ) and not caller.check_permstring(perm):
            caller.msg("Those options are restricted to GMs only.")
            return
        # self.caller.posecount += 1
        if self.cmdstring == "@remit":
            rooms_only = True
            send_to_contents = True
        elif self.cmdstring == "@pemit":
            players_only = True

        if not caller.check_permstring(perm):
            rooms_only = False
            players_only = False

        if not self.rhs or not caller.check_permstring(perm):
            message = args
            message = self.sub_old_ansi(message)
            normal_emit = True
            objnames = []
            do_global = False
        else:
            do_global = True
            message = self.rhs
            message = self.sub_old_ansi(message)
            if caller.check_permstring(perm):
                objnames = self.lhslist
            else:
                objnames = [x.key for x in caller.location.contents if x.player]
        if do_global:
            do_global = caller.check_permstring(perm)
        # normal emits by players are just sent to the room
        if normal_emit:
            # gms = [
            #     ob for ob in caller.location.contents if ob.check_permstring("builders")
            # ]
            non_gms = [
                ob
                for ob in caller.location.contents
                if "emit_label" in ob.tags.all() and ob.player
            ]
            # gm_msg = "{w({c%s{w){n %s" % (caller.name, message)
            # caller.location.msg_contents(
            #     gm_msg, from_obj=caller, options={"is_pose": True}, gm_msg=True
            # )
            caller.location.msg_contents(
                message, from_obj=caller, options={"is_pose": True}
            )
            # for ob in non_gms:
            #     caller.location.msg_contents(
            #     message,
            #     # exclude=gms + non_gms,
            #     from_obj=caller,
            #     options={"is_pose": True},
            #     )
            #     ob.msg(message, from_obj=caller, options={"is_pose": True})
            return
        # send to all objects
        for objname in objnames:
            if players_only:
                obj = caller.player.search(objname)
                if obj:
                    obj = obj.character
            else:
                obj = caller.search(objname, global_search=do_global)
            if not obj:
                caller.msg("Could not find %s." % objname)
                continue
            if rooms_only and obj.location:
                caller.msg("%s is not a room. Ignored." % objname)
                continue
            if players_only and not obj.player:
                caller.msg("%s has no active player. Ignored." % objname)
                continue
            if obj.access(caller, "tell"):
                if obj.check_permstring(perm):
                    bmessage = "{w[Emit by: {c%s{w]{n %s" % (caller.name, message)
                    obj.msg(bmessage, options={"is_pose": True})
                else:
                    obj.msg(message, options={"is_pose": True})
                if send_to_contents and hasattr(obj, "msg_contents"):
                    obj.msg_contents(
                        message, from_obj=caller, kwargs={"options": {"is_pose": True}}
                    )
                    caller.msg("Emitted to %s and contents:\n%s" % (objname, message))
                elif caller.check_permstring(perm):
                    caller.msg("Emitted to %s:\n%s" % (objname, message))
            else:
                caller.msg("You are not allowed to emit to %s." % objname)


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
            caller.msg("Say what OOC?")
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

            name, sex, race, occupation, group, domain, element, quote, profile, lf, maxlf, ap, maxap, ex, maxex, \
            power, knowledge, parry, barrier, speed = self.caller.get_abilities()
            sheetMsg = ""

            sheetMsg += "/\\" + 74 * "_" + "/\\" + "\n"
            nameBorder = "\\/" + (37 - floor(len(name + " - " + occupation)/2.0)) * " "
            nameBorder += name + " - " + occupation
            nameBorder += (76 - len(nameBorder))*" " + "\\/"
            sheetMsg += nameBorder + "\n"
            sheetMsg += "--" + 74 * "-" + "--" + "\n"

            # first row
            firstRow = "| LF"
            firstRow += (22 - (len(str(lf)) + len(str(maxlf)) + 1 + len(firstRow))) * " "
            firstRow += "{0}/{1}".format(lf, maxlf)
            firstRow = self.padToSecondLabel(firstRow)
            firstRow += "Power"
            firstRow = self.padToLastValue(firstRow)
            firstRow += "{0}".format(power)
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
            secondRow += "{0}".format(knowledge)
            secondRow = self.padToEnd(secondRow)
            secondRow += "\n"
            sheetMsg += secondRow

            # third row
            thirdRow = "| AP"
            thirdRow += (22 - (len(str(ap)) + len(str(maxap)) + 1 + len(thirdRow))) * " "
            thirdRow += "{0}/{1}".format(ap, maxap)
            thirdRow = self.padToSecondLabel(thirdRow)
            thirdRow += "Parry"
            thirdRow = self.padToLastValue(thirdRow)
            thirdRow += "{0}".format(parry)
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
            fourthRow += "{0}".format(barrier)
            fourthRow = self.padToEnd(fourthRow)
            fourthRow += "\n"
            sheetMsg += fourthRow

            # fifth row
            fifthRow = "| EX"
            fifthRow += (20 - (len(str(ex)) + len(str(maxex)) + 1 + len(fifthRow))) * " "
            fifthRow += "{0}%/{1}%".format(ex, maxex)
            fifthRow = self.padToSecondLabel(fifthRow)
            fifthRow += "Speed"
            fifthRow = self.padToLastValue(fifthRow)
            fifthRow += "{0}".format(speed)
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

# Here I overwrite "setdesc" from the Evennia master so it has an alias, "@desc."

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

    def sub_old_ansi(self, text):
        """Replacing old ansi with newer evennia markup strings"""
        if not text:
            return ""
        text = text.replace("%r", "|/")
        text = text.replace("%R", "|/")
        text = text.replace("%t", "|-")
        text = text.replace("%T", "|-")
        text = text.replace("%b", "|_")
        text = text.replace("%cr", "|r")
        text = text.replace("%cR", "|[R")
        text = text.replace("%cg", "|g")
        text = text.replace("%cG", "|[G")
        text = text.replace("%cy", "|!Y")
        text = text.replace("%cY", "|[Y")
        text = text.replace("%cb", "|!B")
        text = text.replace("%cB", "|[B")
        text = text.replace("%cm", "|!M")
        text = text.replace("%cM", "|[M")
        text = text.replace("%cc", "|!C")
        text = text.replace("%cC", "|[C")
        text = text.replace("%cw", "|!W")
        text = text.replace("%cW", "|[W")
        text = text.replace("%cx", "|!X")
        text = text.replace("%cX", "|[X")
        text = text.replace("%ch", "|h")
        text = text.replace("%cn", "|n")
        return text

    def func(self):
        """add the description"""

        if not self.args:
            self.caller.msg("You must add a description. Test!")
            return

        self.caller.db.desc = self.args.strip()
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

    def func(self):
        """
        Get all connected accounts by polling session.
        """

        account = self.account
        session_list = SESSIONS.get_sessions()

        session_list = sorted(session_list, key=lambda o: o.account.key)

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
            for session in session_list:
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
                    utils.crop(location, width=25),
                    session.cmd_total,
                    session.protocol_key,
                    isinstance(session.address, tuple) and session.address[0] or session.address,
                )
        else:
            # unprivileged
            table = self.styled_table("|wAccount name", "|wOn for", "|wIdle", "|wRoom")
            for session in session_list:
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
                    utils.crop(location, width=25),
                )
        is_one = naccounts == 1
        self.msg(
            "|wAccounts:|n\n%s\n%s unique account%s logged in."
            % (table, "One" if is_one else naccounts, "" if is_one else "s")
        )

# The mail command from contrib

_HEAD_CHAR = "|015-|n"
_SUB_HEAD_CHAR = "-"
_WIDTH = 78

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
                self.caller, message, receivers=recipient, header=subject
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
        Do the main command functionality
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

# class CmdZog(default_cmds.MuxCommand):
#     """
#     speak but with zog
#     Usage:
#       zog <message>
#     Talk to those in your current location.
#     """
#
#     key = "zog"
#     aliases = ["ziggy"]
#     locks = "cmd:all()"
#
#     def func(self):
#         """Run the zog command"""
#
#         caller = self.caller
#
#         if not self.args:
#             caller.msg("Zog what?")
#             return
#
#         speech = self.args
#
#         # Calling the at_before_say hook on the character
#         speech = caller.at_before_say(speech)
#
#         # If speech is empty, stop here
#         if not speech:
#             return
#
#         # Call the at_after_say hook on the character
#         caller.at_say(speech, msg_self=True)